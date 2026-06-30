import AVFoundation
import Photos
import React
import ReplayKit
import UIKit

@objc(MakeupARLocalMedia)
class MakeupARLocalMedia: NSObject, RCTBridgeModule {
  private let recordingQueue = DispatchQueue(label: "MakeupARLocalMedia.recording")
  private var assetWriter: AVAssetWriter?
  private var videoInput: AVAssetWriterInput?
  private var recordingURL: URL?
  private var hasStartedWriting = false
  private var recordingError: Error?
  private var pendingPhotoResolve: RCTPromiseResolveBlock?
  private var pendingPhotoReject: RCTPromiseRejectBlock?

  static func moduleName() -> String! {
    "MakeupARLocalMedia"
  }

  static func requiresMainQueueSetup() -> Bool {
    true
  }

  @objc(capturePhoto:rejecter:)
  func capturePhoto(
    _ resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    DispatchQueue.main.async {
      guard self.pendingPhotoResolve == nil else {
        reject("photo_busy", "A photo save is already in progress.", nil)
        return
      }

      guard let window = Self.currentKeyWindow() else {
        reject("window_unavailable", "Unable to find a visible app window.", nil)
        return
      }

      let renderer = UIGraphicsImageRenderer(bounds: window.bounds)
      let image = renderer.image { _ in
        window.drawHierarchy(in: window.bounds, afterScreenUpdates: true)
      }

      self.pendingPhotoResolve = resolve
      self.pendingPhotoReject = reject

      PHPhotoLibrary.requestAuthorization(for: .addOnly) { status in
        guard status == .authorized || status == .limited else {
          DispatchQueue.main.async {
            self.clearPhotoPromise()
            reject("photos_denied", "Photo library add permission was denied.", nil)
          }
          return
        }

        DispatchQueue.main.async {
          UIImageWriteToSavedPhotosAlbum(
            image,
            self,
            #selector(self.photoSaveCompleted(_:didFinishSavingWithError:contextInfo:)),
            nil
          )
        }
      }
    }
  }

  @objc(startVideoRecording:rejecter:)
  func startVideoRecording(
    _ resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    let recorder = RPScreenRecorder.shared()
    guard recorder.isAvailable else {
      reject("screen_recording_unavailable", "ReplayKit screen recording is unavailable.", nil)
      return
    }

    recordingQueue.async {
      if self.recordingURL != nil {
        DispatchQueue.main.async {
          reject("video_busy", "A video recording is already in progress.", nil)
        }
        return
      }

      let outputURL = FileManager.default.temporaryDirectory
        .appendingPathComponent("makeup-ar-\(UUID().uuidString).mov")
      try? FileManager.default.removeItem(at: outputURL)
      self.recordingURL = outputURL
      self.assetWriter = nil
      self.videoInput = nil
      self.hasStartedWriting = false
      self.recordingError = nil

      DispatchQueue.main.async {
        recorder.isMicrophoneEnabled = false
        recorder.startCapture(
          handler: { [weak self] sampleBuffer, sampleType, error in
            self?.handleCaptureSample(
              sampleBuffer: sampleBuffer,
              sampleType: sampleType,
              error: error
            )
          },
          completionHandler: { error in
            if let error {
              self.recordingQueue.async {
                self.resetRecordingState(removeTemporaryFile: true)
              }
              reject("video_start_failed", error.localizedDescription, error)
              return
            }

            resolve([
              "status": "recording",
              "mediaType": "video",
            ])
          }
        )
      }
    }
  }

  @objc(stopVideoRecording:rejecter:)
  func stopVideoRecording(
    _ resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    let recorder = RPScreenRecorder.shared()

    recordingQueue.async {
      guard self.recordingURL != nil else {
        DispatchQueue.main.async {
          reject("video_not_recording", "No video recording is in progress.", nil)
        }
        return
      }

      DispatchQueue.main.async {
        recorder.stopCapture { error in
          if let error {
            self.recordingQueue.async {
              self.resetRecordingState(removeTemporaryFile: true)
            }
            reject("video_stop_failed", error.localizedDescription, error)
            return
          }

          self.finishRecording(resolve: resolve, reject: reject)
        }
      }
    }
  }

  @objc
  private func photoSaveCompleted(
    _ image: UIImage,
    didFinishSavingWithError error: Error?,
    contextInfo: UnsafeRawPointer
  ) {
    guard let resolve = pendingPhotoResolve, let reject = pendingPhotoReject else {
      return
    }

    clearPhotoPromise()

    if let error {
      reject("photo_save_failed", error.localizedDescription, error)
      return
    }

    resolve([
      "status": "saved",
      "mediaType": "photo",
    ])
  }

  private func handleCaptureSample(
    sampleBuffer: CMSampleBuffer,
    sampleType: RPSampleBufferType,
    error: Error?
  ) {
    if let error {
      recordingQueue.async {
        self.recordingError = error
      }
      return
    }

    guard sampleType == .video, CMSampleBufferIsValid(sampleBuffer) else {
      return
    }

    recordingQueue.async {
      do {
        try self.prepareWriterIfNeeded(with: sampleBuffer)
      } catch {
        self.recordingError = error
        return
      }

      guard
        let writer = self.assetWriter,
        let input = self.videoInput
      else {
        return
      }

      if writer.status == .unknown {
        writer.startWriting()
        writer.startSession(
          atSourceTime: CMSampleBufferGetPresentationTimeStamp(sampleBuffer)
        )
        self.hasStartedWriting = true
      }

      if writer.status == .writing && input.isReadyForMoreMediaData {
        input.append(sampleBuffer)
      }
    }
  }

  private func prepareWriterIfNeeded(with sampleBuffer: CMSampleBuffer) throws {
    guard assetWriter == nil else {
      return
    }

    guard let outputURL = recordingURL else {
      return
    }

    guard let formatDescription = CMSampleBufferGetFormatDescription(sampleBuffer) else {
      throw NSError(
        domain: "MakeupARLocalMedia",
        code: 1,
        userInfo: [NSLocalizedDescriptionKey: "Missing video format description."]
      )
    }

    let dimensions = CMVideoFormatDescriptionGetDimensions(formatDescription)
    let settings: [String: Any] = [
      AVVideoCodecKey: AVVideoCodecType.h264,
      AVVideoWidthKey: Int(dimensions.width),
      AVVideoHeightKey: Int(dimensions.height),
    ]
    let writer = try AVAssetWriter(outputURL: outputURL, fileType: .mov)
    let input = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
    input.expectsMediaDataInRealTime = true

    guard writer.canAdd(input) else {
      throw NSError(
        domain: "MakeupARLocalMedia",
        code: 2,
        userInfo: [NSLocalizedDescriptionKey: "Unable to add video input."]
      )
    }

    writer.add(input)
    assetWriter = writer
    videoInput = input
  }

  private func finishRecording(
    resolve: @escaping RCTPromiseResolveBlock,
    reject: @escaping RCTPromiseRejectBlock
  ) {
    recordingQueue.async {
      if let recordingError = self.recordingError {
        self.resetRecordingState(removeTemporaryFile: true)
        reject("video_recording_failed", recordingError.localizedDescription, recordingError)
        return
      }

      guard
        let outputURL = self.recordingURL,
        let writer = self.assetWriter,
        let input = self.videoInput,
        self.hasStartedWriting
      else {
        self.resetRecordingState(removeTemporaryFile: true)
        reject("video_empty", "No video frames were captured.", nil)
        return
      }

      input.markAsFinished()
      writer.finishWriting {
        if writer.status != .completed {
          let error = writer.error
          self.recordingQueue.async {
            self.resetRecordingState(removeTemporaryFile: true)
          }
          reject(
            "video_write_failed",
            error?.localizedDescription ?? "Video writer did not complete.",
            error
          )
          return
        }

        self.saveVideoToPhotoLibrary(
          outputURL,
          resolve: resolve,
          reject: reject
        )
      }
    }
  }

  private func saveVideoToPhotoLibrary(
    _ outputURL: URL,
    resolve: @escaping RCTPromiseResolveBlock,
    reject: @escaping RCTPromiseRejectBlock
  ) {
    PHPhotoLibrary.requestAuthorization(for: .addOnly) { status in
      guard status == .authorized || status == .limited else {
        self.recordingQueue.async {
          self.resetRecordingState(removeTemporaryFile: true)
        }
        reject("photos_denied", "Photo library add permission was denied.", nil)
        return
      }

      var localIdentifier: String?
      PHPhotoLibrary.shared().performChanges {
        let request = PHAssetChangeRequest.creationRequestForAssetFromVideo(
          atFileURL: outputURL
        )
        localIdentifier = request?.placeholderForCreatedAsset?.localIdentifier
      } completionHandler: { success, error in
        self.recordingQueue.async {
          self.resetRecordingState(removeTemporaryFile: true)
        }

        if let error {
          reject("video_save_failed", error.localizedDescription, error)
          return
        }

        guard success else {
          reject("video_save_failed", "Photo library video save did not complete.", nil)
          return
        }

        resolve([
          "status": "saved",
          "mediaType": "video",
          "localIdentifier": localIdentifier ?? "",
        ])
      }
    }
  }

  private func clearPhotoPromise() {
    pendingPhotoResolve = nil
    pendingPhotoReject = nil
  }

  private func resetRecordingState(removeTemporaryFile: Bool) {
    let outputURL = recordingURL
    assetWriter = nil
    videoInput = nil
    recordingURL = nil
    hasStartedWriting = false
    recordingError = nil

    if removeTemporaryFile, let outputURL {
      try? FileManager.default.removeItem(at: outputURL)
    }
  }

  private static func currentKeyWindow() -> UIWindow? {
    UIApplication.shared.connectedScenes
      .compactMap { $0 as? UIWindowScene }
      .flatMap { $0.windows }
      .first { $0.isKeyWindow }
  }
}
