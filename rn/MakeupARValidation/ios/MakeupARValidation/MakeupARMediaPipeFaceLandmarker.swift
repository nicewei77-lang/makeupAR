import Foundation
import CoreImage
import CoreVideo
import ImageIO
import UIKit
import MediaPipeTasksVision

@objc(MakeupARMediaPipeFaceLandmarker)
final class MakeupARMediaPipeFaceLandmarker: NSObject {
  // Privacy contract: raw camera frames are memory-only. Detector diagnostics
  // are limited to landmark, bbox, confidence, timing, and status numbers.
  @objc static let dependencyLinked = true

  @objc static func bundledModelPath() -> String? {
    Bundle.main.path(forResource: "face_landmarker", ofType: "task")
  }
}

private enum MakeupARMediaPipeFullFaceRuntime {
  private static let lock = NSLock()
  private static var cachedVideoLandmarker: FaceLandmarker?
  private static var cachedImageLandmarker: FaceLandmarker?
  private static var lastTimestampMs: Int64 = 0
  private static var preferredOrientationDegrees: Int32?
  private static var nextImageReacquireWallClockMs: Int64 = 0
  private static var nextUiImageReacquireWallClockMs: Int64 = 0
  private static var fullFaceFrameCount = 0
  private static var videoFaceCount = 0
  private static var videoNoFaceCount = 0
  private static var imageReacquireTriggerCount = 0
  private static var imageReacquireTotalAttemptCount = 0
  private static var imageReacquireSuccessCount = 0
  private static var imageReacquireNoFaceCount = 0
  private static var uiImageReacquireTriggerCount = 0
  private static var uiImageReacquireTotalAttemptCount = 0
  private static var uiImageReacquireSuccessCount = 0
  private static var uiImageReacquireNoFaceCount = 0
  private static let frameSource = MakeupARMediaPipeFrameSource()
  private static let ciContext = CIContext(options: nil)

  private static let source = "mediapipe_face_landmarker_full_face_v1"
  private static let coordinateMode = "normalized-image"
  private static let inputFormat = "bgra-cvpixelbuffer"

  static func detectFullFaceBgra(
    bytes: UnsafePointer<UInt8>?,
    byteCount: Int32,
    imageWidth: Int32,
    imageHeight: Int32,
    timestampMs: Int64,
    orientationDegrees: Int32
  ) -> String {
    let startedAt = Date()

    guard let bytes, byteCount > 0, imageWidth > 0, imageHeight > 0 else {
      return failureJson(
        status: "invalid_input",
        detail: "bgra_bytes_empty_or_invalid_dimensions",
        imageWidth: imageWidth,
        imageHeight: imageHeight,
        timestampMs: timestampMs,
        startedAt: startedAt
      )
    }

    let expectedMinimumByteCount = Int(imageWidth) * Int(imageHeight) * 4
    guard Int(byteCount) >= expectedMinimumByteCount else {
      return failureJson(
        status: "invalid_input",
        detail: "bgra_byte_count_too_small",
        imageWidth: imageWidth,
        imageHeight: imageHeight,
        timestampMs: timestampMs,
        startedAt: startedAt
      )
    }

    do {
      let pixelBuffer = try makePixelBuffer(
        bytes: bytes,
        byteCount: Int(byteCount),
        width: Int(imageWidth),
        height: Int(imageHeight)
      )
      let frame = frameSource.makeFrame(
        pixelBuffer: pixelBuffer,
        timestampMs: timestampMs,
        orientation: cgImageOrientation(forDegrees: orientationDegrees)
      )
      return try detectFullFaceFrame(
        frame: frame,
        imageWidth: imageWidth,
        imageHeight: imageHeight,
        requestedOrientationDegrees: orientationDegrees,
        startedAt: startedAt
      )
    } catch {
      return failureJson(
        status: "mediapipe_failed",
        detail: error.localizedDescription,
        imageWidth: imageWidth,
        imageHeight: imageHeight,
        timestampMs: timestampMs,
        startedAt: startedAt,
        requestedOrientationDegrees: orientationDegrees,
        selectedOrientationDegrees: normalizeOrientationDegrees(orientationDegrees),
        orientationFallbackTried: false,
        orientationAttemptDegrees: []
      )
    }
  }

  static func detectFullFaceNativeFrameNotConnected(
    frameHandle: Int64,
    timestampMs: Int64
  ) -> String {
    """
    {"status":"not_connected","detail":"native_frame_handle_not_connected","source":"\(source)","coordinateMode":"\(coordinateMode)","inputFormat":"native-cvpixelbuffer","frameId":\(timestampMs),"timestampMs":\(timestampMs),"imageWidth":0,"imageHeight":0,"faceCount":0,"landmarkCount":0,"hasBlendshapes":false,"blendshapeCount":0,"hasFacialTransformMatrix":false,"facialTransformMatrixCount":0,"faceConfidence":0,"latencyMs":0,"nativeFrameHandle":\(frameHandle),"available":false,"rawFrameStored":false,"offDeviceUpload":false}
    """
  }

  private static func detectFullFaceFrame(
    frame: MakeupARMediaPipeFrameSource.Frame,
    imageWidth: Int32,
    imageHeight: Int32,
    requestedOrientationDegrees: Int32?,
    startedAt: Date
  ) throws -> String {
    let width = imageWidth > 0 ? imageWidth : Int32(CVPixelBufferGetWidth(frame.pixelBuffer))
    let height = imageHeight > 0 ? imageHeight : Int32(CVPixelBufferGetHeight(frame.pixelBuffer))
    incrementFullFaceFrameCount()
    let orientationDegrees =
      requestedOrientationDegrees ?? orientationDegrees(for: frame.orientation)
    let landmarker = try getVideoLandmarker()
    let detection = try detectWithOrientationFallback(
      pixelBuffer: frame.pixelBuffer,
      landmarker: landmarker,
      requestedOrientationDegrees: orientationDegrees,
      timestampMs: frame.timestampMs
    )
    let result = detection.result

    guard let face = result.faceLandmarks.first, !face.isEmpty else {
      return failureJson(
        status: "no_face",
        detail: "no_face_landmarks",
        imageWidth: width,
        imageHeight: height,
        timestampMs: detection.timestampMs,
        startedAt: startedAt,
        requestedOrientationDegrees: orientationDegrees,
        selectedOrientationDegrees: detection.selectedOrientationDegrees,
        orientationFallbackTried: detection.fallbackTried,
        orientationAttemptDegrees: detection.attemptedOrientationDegrees,
        detectionMode: detection.detectionMode,
        imageReacquireAttempted: detection.imageReacquireAttempted,
        imageReacquireAttemptCount: detection.imageReacquireAttemptCount
      )
    }

    let latencyMs = Int(Date().timeIntervalSince(startedAt) * 1000.0)
    let confidence = averagePresence(face: face)
    let bbox = bboxJson(face: face)
    let landmarks = landmarksJson(face: face)
    let matrixCount = result.facialTransformationMatrixes.count
    let blendshapeCount = result.faceBlendshapes.count

    return """
    {"status":"ok","detail":"full_face_landmarks","source":"\(source)","coordinateMode":"\(coordinateMode)","inputFormat":"\(inputFormat)","frameId":\(detection.timestampMs),"timestampMs":\(detection.timestampMs),"imageWidth":\(width),"imageHeight":\(height),"faceCount":\(result.faceLandmarks.count),"landmarkCount":\(face.count),"hasBlendshapes":\(blendshapeCount > 0),"blendshapeCount":\(blendshapeCount),"hasFacialTransformMatrix":\(matrixCount > 0),"facialTransformMatrixCount":\(matrixCount),"faceConfidence":\(format(confidence)),"latencyMs":\(latencyMs),"requestedOrientationDegrees":\(orientationDegrees),"selectedOrientationDegrees":\(detection.selectedOrientationDegrees),"orientationFallbackTried":\(detection.fallbackTried),"orientationAttemptCount":\(detection.attemptedOrientationDegrees.count),"orientationAttemptDegrees":\(intArrayJson(detection.attemptedOrientationDegrees)),"detectionMode":"\(escape(detection.detectionMode))","imageReacquireAttempted":\(detection.imageReacquireAttempted),"imageReacquireAttemptCount":\(detection.imageReacquireAttemptCount),\(diagnosticCounterJsonFields()),"bbox":\(bbox),"landmarks":\(landmarks),"rawFrameStored":false,"offDeviceUpload":false}
    """
  }

  private static func detectWithOrientationFallback(
    pixelBuffer: CVPixelBuffer,
    landmarker: FaceLandmarker,
    requestedOrientationDegrees: Int32,
    timestampMs: Int64
  ) throws -> (
    result: FaceLandmarkerResult,
    selectedOrientationDegrees: Int32,
    attemptedOrientationDegrees: [Int32],
    fallbackTried: Bool,
    timestampMs: Int64,
    detectionMode: String,
    imageReacquireAttempted: Bool,
    imageReacquireAttemptCount: Int
  ) {
    let candidates = orientationCandidates(requestedDegrees: requestedOrientationDegrees)
    var attemptedDegrees: [Int32] = []
    var lastResult: FaceLandmarkerResult?
    var lastDetectionTimestampMs = timestampMs

    for candidate in candidates {
      let mpImage = try MPImage(
        pixelBuffer: pixelBuffer,
        orientation: imageOrientation(forDegrees: candidate)
      )
      let detectionTimestampMs = nextMonotonicTimestamp(
        timestampMs + Int64(attemptedDegrees.count)
      )
      let result = try landmarker.detect(
        videoFrame: mpImage,
        timestampInMilliseconds: Int(detectionTimestampMs)
      )

      attemptedDegrees.append(candidate)
      lastResult = result
      lastDetectionTimestampMs = detectionTimestampMs

      if let face = result.faceLandmarks.first, !face.isEmpty {
        setPreferredOrientationDegrees(candidate)
        recordVideoFace()
        return (
          result,
          candidate,
          attemptedDegrees,
          attemptedDegrees.count > 1,
          detectionTimestampMs,
          "video",
          false,
          0
        )
      }
    }

    recordVideoNoFace()
    var imageReacquireAttempted = false
    var imageReacquireAttemptCount = 0
    if shouldAttemptImageReacquire() {
      imageReacquireAttempted = true
      recordImageReacquireTriggered()
      if let imageReacquire = try tryDetectImageReacquire(
        pixelBuffer: pixelBuffer,
        orientationCandidates: candidates,
        attemptedDegrees: attemptedDegrees,
        timestampMs: timestampMs,
        imageReacquireAttemptCount: &imageReacquireAttemptCount
       ) {
        recordImageReacquireResult(attempts: imageReacquireAttemptCount, success: true)
        return imageReacquire
      }
      recordImageReacquireResult(attempts: imageReacquireAttemptCount, success: false)
    }

    if shouldAttemptUiImageReacquire() {
      imageReacquireAttempted = true
      recordUiImageReacquireTriggered()
      let attemptsBeforeUiImage = imageReacquireAttemptCount
      if let uiImageReacquire = try tryDetectUiImageReacquire(
        pixelBuffer: pixelBuffer,
        orientationCandidates: candidates,
        attemptedDegrees: attemptedDegrees,
        timestampMs: timestampMs,
        imageReacquireAttemptCount: &imageReacquireAttemptCount
      ) {
        recordUiImageReacquireResult(
          attempts: imageReacquireAttemptCount - attemptsBeforeUiImage,
          success: true
        )
        return uiImageReacquire
      }
      recordUiImageReacquireResult(
        attempts: imageReacquireAttemptCount - attemptsBeforeUiImage,
        success: false
      )
    }

    guard let lastResult else {
      throw NSError(
        domain: "MakeupARMediaPipeFaceLandmarker",
        code: 4,
        userInfo: [NSLocalizedDescriptionKey: "No orientation attempts were executed."]
      )
    }

    return (
      lastResult,
      attemptedDegrees.last ?? normalizeOrientationDegrees(requestedOrientationDegrees),
      attemptedDegrees,
      attemptedDegrees.count > 1,
      lastDetectionTimestampMs,
      "video",
      imageReacquireAttempted,
      imageReacquireAttemptCount
    )
  }

  private static func tryDetectImageReacquire(
    pixelBuffer: CVPixelBuffer,
    orientationCandidates: [Int32],
    attemptedDegrees: [Int32],
    timestampMs: Int64,
    imageReacquireAttemptCount: inout Int
  ) throws -> (
    result: FaceLandmarkerResult,
    selectedOrientationDegrees: Int32,
    attemptedOrientationDegrees: [Int32],
    fallbackTried: Bool,
    timestampMs: Int64,
    detectionMode: String,
    imageReacquireAttempted: Bool,
    imageReacquireAttemptCount: Int
  )? {
    let landmarker = try getImageLandmarker()
    var nextAttemptedDegrees = attemptedDegrees
    var detectionTimestampMs = timestampMs

    for candidate in orientationCandidates {
      let mpImage = try MPImage(
        pixelBuffer: pixelBuffer,
        orientation: imageOrientation(forDegrees: candidate)
      )
      detectionTimestampMs = nextMonotonicTimestamp(
        timestampMs + Int64(nextAttemptedDegrees.count)
      )
      let result = try landmarker.detect(image: mpImage)
      nextAttemptedDegrees.append(candidate)
      imageReacquireAttemptCount += 1

      if let face = result.faceLandmarks.first, !face.isEmpty {
        setPreferredOrientationDegrees(candidate)
        return (
          result,
          candidate,
          nextAttemptedDegrees,
          true,
          detectionTimestampMs,
          "image_reacquire",
          true,
          imageReacquireAttemptCount
        )
      }
    }

    return nil
  }

  private static func tryDetectUiImageReacquire(
    pixelBuffer: CVPixelBuffer,
    orientationCandidates: [Int32],
    attemptedDegrees: [Int32],
    timestampMs: Int64,
    imageReacquireAttemptCount: inout Int
  ) throws -> (
    result: FaceLandmarkerResult,
    selectedOrientationDegrees: Int32,
    attemptedOrientationDegrees: [Int32],
    fallbackTried: Bool,
    timestampMs: Int64,
    detectionMode: String,
    imageReacquireAttempted: Bool,
    imageReacquireAttemptCount: Int
  )? {
    let landmarker = try getImageLandmarker()
    let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
    let extent = CGRect(
      x: 0,
      y: 0,
      width: CGFloat(CVPixelBufferGetWidth(pixelBuffer)),
      height: CGFloat(CVPixelBufferGetHeight(pixelBuffer))
    )
    guard let cgImage = ciContext.createCGImage(ciImage, from: extent) else {
      return nil
    }

    var nextAttemptedDegrees = attemptedDegrees
    var detectionTimestampMs = timestampMs

    for candidate in orientationCandidates {
      let uiImage = UIImage(cgImage: cgImage, scale: 1.0, orientation: .up)
      let mpImage = try MPImage(
        uiImage: uiImage,
        orientation: imageOrientation(forDegrees: candidate)
      )
      detectionTimestampMs = nextMonotonicTimestamp(
        timestampMs + Int64(nextAttemptedDegrees.count)
      )
      let result = try landmarker.detect(image: mpImage)
      nextAttemptedDegrees.append(candidate)
      imageReacquireAttemptCount += 1

      if let face = result.faceLandmarks.first, !face.isEmpty {
        setPreferredOrientationDegrees(candidate)
        return (
          result,
          candidate,
          nextAttemptedDegrees,
          true,
          detectionTimestampMs,
          "uiimage_reacquire",
          true,
          imageReacquireAttemptCount
        )
      }
    }

    return nil
  }

  private static func shouldAttemptImageReacquire() -> Bool {
    lock.lock()
    defer { lock.unlock() }

    let nowMs = Int64(Date().timeIntervalSince1970 * 1000.0)
    if nowMs < nextImageReacquireWallClockMs {
      return false
    }

    nextImageReacquireWallClockMs = nowMs + 500
    return true
  }

  private static func shouldAttemptUiImageReacquire() -> Bool {
    lock.lock()
    defer { lock.unlock() }

    let nowMs = Int64(Date().timeIntervalSince1970 * 1000.0)
    if nowMs < nextUiImageReacquireWallClockMs {
      return false
    }

    nextUiImageReacquireWallClockMs = nowMs + 2000
    return true
  }

  private static func getVideoLandmarker() throws -> FaceLandmarker {
    lock.lock()
    defer { lock.unlock() }

    if let cachedVideoLandmarker {
      return cachedVideoLandmarker
    }

    guard let modelPath = MakeupARMediaPipeFaceLandmarker.bundledModelPath() else {
      throw NSError(
        domain: "MakeupARMediaPipeFaceLandmarker",
        code: 1,
        userInfo: [NSLocalizedDescriptionKey: "face_landmarker.task missing from app bundle."]
      )
    }

    let baseOptions = BaseOptions()
    baseOptions.modelAssetPath = modelPath

    let options = FaceLandmarkerOptions()
    options.baseOptions = baseOptions
    options.runningMode = .video
    options.numFaces = 1
    options.minFaceDetectionConfidence = 0.45
    options.minFacePresenceConfidence = 0.45
    options.minTrackingConfidence = 0.45
    options.outputFaceBlendshapes = false
    options.outputFacialTransformationMatrixes = true

    let landmarker = try FaceLandmarker(options: options)
    cachedVideoLandmarker = landmarker
    return landmarker
  }

  private static func getImageLandmarker() throws -> FaceLandmarker {
    lock.lock()
    defer { lock.unlock() }

    if let cachedImageLandmarker {
      return cachedImageLandmarker
    }

    guard let modelPath = MakeupARMediaPipeFaceLandmarker.bundledModelPath() else {
      throw NSError(
        domain: "MakeupARMediaPipeFaceLandmarker",
        code: 5,
        userInfo: [NSLocalizedDescriptionKey: "face_landmarker.task missing from app bundle."]
      )
    }

    let baseOptions = BaseOptions()
    baseOptions.modelAssetPath = modelPath

    let options = FaceLandmarkerOptions()
    options.baseOptions = baseOptions
    options.runningMode = .image
    options.numFaces = 1
    options.minFaceDetectionConfidence = 0.35
    options.minFacePresenceConfidence = 0.35
    options.minTrackingConfidence = 0.35
    options.outputFaceBlendshapes = false
    options.outputFacialTransformationMatrixes = true

    let landmarker = try FaceLandmarker(options: options)
    cachedImageLandmarker = landmarker
    return landmarker
  }

  private static func makePixelBuffer(
    bytes: UnsafePointer<UInt8>,
    byteCount: Int,
    width: Int,
    height: Int
  ) throws -> CVPixelBuffer {
    let attributes = [
      kCVPixelBufferCGImageCompatibilityKey: true,
      kCVPixelBufferCGBitmapContextCompatibilityKey: true,
      kCVPixelBufferIOSurfacePropertiesKey: [:],
    ] as CFDictionary
    var pixelBuffer: CVPixelBuffer?
    let status = CVPixelBufferCreate(
      kCFAllocatorDefault,
      width,
      height,
      kCVPixelFormatType_32BGRA,
      attributes,
      &pixelBuffer
    )

    guard status == kCVReturnSuccess, let pixelBuffer else {
      throw NSError(
        domain: "MakeupARMediaPipeFaceLandmarker",
        code: 2,
        userInfo: [NSLocalizedDescriptionKey: "Unable to allocate BGRA CVPixelBuffer."]
      )
    }

    CVPixelBufferLockBaseAddress(pixelBuffer, [])
    defer {
      CVPixelBufferUnlockBaseAddress(pixelBuffer, [])
    }

    guard let destination = CVPixelBufferGetBaseAddress(pixelBuffer) else {
      throw NSError(
        domain: "MakeupARMediaPipeFaceLandmarker",
        code: 3,
        userInfo: [NSLocalizedDescriptionKey: "Unable to access CVPixelBuffer base address."]
      )
    }

    let destinationRowBytes = CVPixelBufferGetBytesPerRow(pixelBuffer)
    let sourceRowBytes = width * 4
    let rowsToCopy = min(height, byteCount / sourceRowBytes)

    for row in 0..<rowsToCopy {
      let sourcePointer = bytes.advanced(by: row * sourceRowBytes)
      let destinationPointer = destination.advanced(by: row * destinationRowBytes)
      memcpy(destinationPointer, sourcePointer, sourceRowBytes)
    }

    return pixelBuffer
  }

  private static func nextMonotonicTimestamp(_ timestampMs: Int64) -> Int64 {
    lock.lock()
    defer { lock.unlock() }

    let candidate = timestampMs > 0 ? timestampMs : Int64(Date().timeIntervalSince1970 * 1000.0)
    let monotonic = candidate > lastTimestampMs ? candidate : lastTimestampMs + 1
    lastTimestampMs = monotonic
    return monotonic
  }

  private static func incrementFullFaceFrameCount() {
    lock.lock()
    fullFaceFrameCount += 1
    lock.unlock()
  }

  private static func recordVideoFace() {
    lock.lock()
    videoFaceCount += 1
    lock.unlock()
  }

  private static func recordVideoNoFace() {
    lock.lock()
    videoNoFaceCount += 1
    lock.unlock()
  }

  private static func recordImageReacquireTriggered() {
    lock.lock()
    imageReacquireTriggerCount += 1
    lock.unlock()
  }

  private static func recordImageReacquireResult(attempts: Int, success: Bool) {
    lock.lock()
    imageReacquireTotalAttemptCount += max(0, attempts)
    if success {
      imageReacquireSuccessCount += 1
    } else {
      imageReacquireNoFaceCount += 1
    }
    lock.unlock()
  }

  private static func recordUiImageReacquireTriggered() {
    lock.lock()
    uiImageReacquireTriggerCount += 1
    lock.unlock()
  }

  private static func recordUiImageReacquireResult(attempts: Int, success: Bool) {
    lock.lock()
    uiImageReacquireTotalAttemptCount += max(0, attempts)
    if success {
      uiImageReacquireSuccessCount += 1
    } else {
      uiImageReacquireNoFaceCount += 1
    }
    lock.unlock()
  }

  private static func diagnosticCounterJsonFields() -> String {
    lock.lock()
    let frameCount = fullFaceFrameCount
    let videoHits = videoFaceCount
    let videoMisses = videoNoFaceCount
    let reacquireTriggers = imageReacquireTriggerCount
    let reacquireAttempts = imageReacquireTotalAttemptCount
    let reacquireHits = imageReacquireSuccessCount
    let reacquireMisses = imageReacquireNoFaceCount
    let uiReacquireTriggers = uiImageReacquireTriggerCount
    let uiReacquireAttempts = uiImageReacquireTotalAttemptCount
    let uiReacquireHits = uiImageReacquireSuccessCount
    let uiReacquireMisses = uiImageReacquireNoFaceCount
    lock.unlock()

    return """
    "fullFaceFrameCount":\(frameCount),"videoFaceCount":\(videoHits),"videoNoFaceCount":\(videoMisses),"imageReacquireTriggerCount":\(reacquireTriggers),"imageReacquireTotalAttemptCount":\(reacquireAttempts),"imageReacquireSuccessCount":\(reacquireHits),"imageReacquireNoFaceCount":\(reacquireMisses),"uiImageReacquireTriggerCount":\(uiReacquireTriggers),"uiImageReacquireTotalAttemptCount":\(uiReacquireAttempts),"uiImageReacquireSuccessCount":\(uiReacquireHits),"uiImageReacquireNoFaceCount":\(uiReacquireMisses)
    """
  }

  private static func orientationCandidates(requestedDegrees: Int32) -> [Int32] {
    let requested = normalizeOrientationDegrees(requestedDegrees)
    var candidates: [Int32] = []

    if let preferred = getPreferredOrientationDegrees() {
      candidates.append(preferred)
    }

    candidates.append(requested)
    candidates.append(contentsOf: [0, 90, 180, 270])

    var unique: [Int32] = []
    for candidate in candidates {
      let normalized = normalizeOrientationDegrees(candidate)
      if !unique.contains(normalized) {
        unique.append(normalized)
      }
    }

    return unique
  }

  private static func getPreferredOrientationDegrees() -> Int32? {
    lock.lock()
    defer { lock.unlock() }
    return preferredOrientationDegrees
  }

  private static func setPreferredOrientationDegrees(_ degrees: Int32) {
    lock.lock()
    preferredOrientationDegrees = normalizeOrientationDegrees(degrees)
    lock.unlock()
  }

  private static func normalizeOrientationDegrees(_ degrees: Int32) -> Int32 {
    let normalized = degrees % 360
    return normalized >= 0 ? normalized : normalized + 360
  }

  private static func imageOrientation(forDegrees degrees: Int32) -> UIImage.Orientation {
    switch normalizeOrientationDegrees(degrees) {
    case 90:
      return .right
    case 180:
      return .down
    case 270:
      return .left
    default:
      return .up
    }
  }

  private static func cgImageOrientation(forDegrees degrees: Int32) -> CGImagePropertyOrientation {
    switch normalizeOrientationDegrees(degrees) {
    case 90:
      return .right
    case 180:
      return .down
    case 270:
      return .left
    default:
      return .up
    }
  }

  private static func orientationDegrees(for orientation: CGImagePropertyOrientation) -> Int32 {
    switch orientation {
    case .right, .rightMirrored:
      return 90
    case .down, .downMirrored:
      return 180
    case .left, .leftMirrored:
      return 270
    default:
      return 0
    }
  }

  private static func landmarksJson(face: [NormalizedLandmark]) -> String {
    let points = face.enumerated().map { index, landmark in
      let presence = landmark.presence?.floatValue ?? 1.0
      return """
      {"i":\(index),"x":\(format(landmark.x)),"y":\(format(landmark.y)),"z":\(format(landmark.z)),"presence":\(format(presence))}
      """
    }

    return "[\(points.joined(separator: ","))]"
  }

  private static func intArrayJson(_ values: [Int32]) -> String {
    "[\(values.map { String($0) }.joined(separator: ","))]"
  }

  private static func bboxJson(face: [NormalizedLandmark]) -> String {
    guard let first = face.first else {
      return "{\"left\":0,\"top\":0,\"right\":0,\"bottom\":0,\"width\":0,\"height\":0}"
    }

    var left = first.x
    var right = first.x
    var top = first.y
    var bottom = first.y

    for landmark in face {
      left = min(left, landmark.x)
      right = max(right, landmark.x)
      top = min(top, landmark.y)
      bottom = max(bottom, landmark.y)
    }

    return """
    {"left":\(format(left)),"top":\(format(top)),"right":\(format(right)),"bottom":\(format(bottom)),"width":\(format(right - left)),"height":\(format(bottom - top))}
    """
  }

  private static func averagePresence(face: [NormalizedLandmark]) -> Float {
    guard !face.isEmpty else {
      return 0.0
    }

    var total: Float = 0
    for landmark in face {
      total += landmark.presence?.floatValue ?? 1.0
    }

    return total / Float(face.count)
  }

  private static func failureJson(
    status: String,
    detail: String,
    imageWidth: Int32,
    imageHeight: Int32,
    timestampMs: Int64,
    startedAt: Date,
    requestedOrientationDegrees: Int32 = 0,
    selectedOrientationDegrees: Int32 = 0,
    orientationFallbackTried: Bool = false,
    orientationAttemptDegrees: [Int32] = [],
    detectionMode: String = "video",
    imageReacquireAttempted: Bool = false,
    imageReacquireAttemptCount: Int = 0
  ) -> String {
    let latencyMs = Int(Date().timeIntervalSince(startedAt) * 1000.0)
    return """
    {"status":"\(escape(status))","detail":"\(escape(detail))","source":"\(source)","coordinateMode":"\(coordinateMode)","inputFormat":"\(inputFormat)","frameId":\(timestampMs),"timestampMs":\(timestampMs),"imageWidth":\(imageWidth),"imageHeight":\(imageHeight),"faceCount":0,"landmarkCount":0,"hasBlendshapes":false,"blendshapeCount":0,"hasFacialTransformMatrix":false,"facialTransformMatrixCount":0,"faceConfidence":0,"latencyMs":\(latencyMs),"requestedOrientationDegrees":\(requestedOrientationDegrees),"selectedOrientationDegrees":\(selectedOrientationDegrees),"orientationFallbackTried":\(orientationFallbackTried),"orientationAttemptCount":\(orientationAttemptDegrees.count),"orientationAttemptDegrees":\(intArrayJson(orientationAttemptDegrees)),"detectionMode":"\(escape(detectionMode))","imageReacquireAttempted":\(imageReacquireAttempted),"imageReacquireAttemptCount":\(imageReacquireAttemptCount),\(diagnosticCounterJsonFields()),"bbox":{"left":0,"top":0,"right":0,"bottom":0,"width":0,"height":0},"landmarks":[],"rawFrameStored":false,"offDeviceUpload":false}
    """
  }

  private static func format(_ value: Float) -> String {
    String(format: "%.6f", value)
  }

  private static func escape(_ value: String) -> String {
    value
      .replacingOccurrences(of: "\\", with: "\\\\")
      .replacingOccurrences(of: "\"", with: "\\\"")
      .replacingOccurrences(of: "\n", with: "\\n")
      .replacingOccurrences(of: "\r", with: "\\r")
  }
}

private enum MakeupARMediaPipeBrowRuntime {
  private static let lock = NSLock()
  private static var cachedLandmarker: FaceLandmarker?

  private static let source = "mediapipe_face_landmarker_runtime_brow_landmarks"
  private static let coordinateMode = "normalized-image"

  static func detectBrowLandmarksPng(
    bytes: UnsafePointer<UInt8>?,
    byteCount: Int32,
    imageWidth: Int32,
    imageHeight: Int32
  ) -> String {
    // diagnostic-only legacy path. Product MediaPipe runtime uses BGRA camera
    // frames through E7MediaPipeAppDetectFullFaceBgra instead of PNG bytes.
    let startedAt = Date()

    guard let bytes, byteCount > 0 else {
      return failureJson(
        status: "invalid_input",
        detail: "png_bytes_empty",
        imageWidth: imageWidth,
        imageHeight: imageHeight,
        startedAt: startedAt
      )
    }

    let data = Data(bytes: bytes, count: Int(byteCount))
    guard let image = UIImage(data: data) else {
      return failureJson(
        status: "decode_failed",
        detail: "ui_image_decode_failed",
        imageWidth: imageWidth,
        imageHeight: imageHeight,
        startedAt: startedAt
      )
    }

    do {
      let mpImage = try MPImage(uiImage: image, orientation: .up)
      let landmarker = try getLandmarker()
      let result = try landmarker.detect(image: mpImage)
      guard let face = result.faceLandmarks.first, !face.isEmpty else {
        return failureJson(
          status: "no_face",
          detail: "no_face_landmarks",
          imageWidth: Int32(image.size.width),
          imageHeight: Int32(image.size.height),
          startedAt: startedAt
        )
      }

      let leftIndexes = eyebrowIndexes(from: FaceLandmarker.leftEyebrowConnections())
      let rightIndexes = eyebrowIndexes(from: FaceLandmarker.rightEyebrowConnections())
      let leftPoints = pointsJson(face: face, indexes: leftIndexes)
      let rightPoints = pointsJson(face: face, indexes: rightIndexes)
      let bbox = bboxJson(face: face)
      let confidence = averagePresence(face: face, indexes: leftIndexes + rightIndexes)
      let latencyMs = Int(Date().timeIntervalSince(startedAt) * 1000.0)

      return """
      {"status":"ok","detail":"left_right_eyebrow_landmarks","source":"\(source)","coordinateMode":"\(coordinateMode)","imageWidth":\(Int(image.size.width)),"imageHeight":\(Int(image.size.height)),"faceCount":\(result.faceLandmarks.count),"landmarkCount":\(face.count),"leftPointCount":\(leftIndexes.count),"rightPointCount":\(rightIndexes.count),"confidence":\(format(confidence)),"latencyMs":\(latencyMs),"bbox":\(bbox),"leftEyebrow":\(leftPoints),"rightEyebrow":\(rightPoints),"rawCameraFrameStored":false,"offDeviceUpload":false}
      """
    } catch {
      return failureJson(
        status: "mediapipe_failed",
        detail: error.localizedDescription,
        imageWidth: imageWidth,
        imageHeight: imageHeight,
        startedAt: startedAt
      )
    }
  }

  private static func getLandmarker() throws -> FaceLandmarker {
    lock.lock()
    defer { lock.unlock() }

    if let cachedLandmarker {
      return cachedLandmarker
    }

    guard let modelPath = MakeupARMediaPipeFaceLandmarker.bundledModelPath() else {
      throw NSError(
        domain: "MakeupARMediaPipeFaceLandmarker",
        code: 1,
        userInfo: [NSLocalizedDescriptionKey: "face_landmarker.task missing from app bundle."]
      )
    }

    let baseOptions = BaseOptions()
    baseOptions.modelAssetPath = modelPath

    let options = FaceLandmarkerOptions()
    options.baseOptions = baseOptions
    options.runningMode = .image
    options.numFaces = 1
    options.minFaceDetectionConfidence = 0.45
    options.minFacePresenceConfidence = 0.45
    options.minTrackingConfidence = 0.45
    options.outputFaceBlendshapes = false
    options.outputFacialTransformationMatrixes = true

    let landmarker = try FaceLandmarker(options: options)
    cachedLandmarker = landmarker
    return landmarker
  }

  private static func eyebrowIndexes(from connections: [Connection]) -> [Int] {
    var indexes = Set<Int>()
    for connection in connections {
      indexes.insert(Int(connection.start))
      indexes.insert(Int(connection.end))
    }

    return indexes.sorted()
  }

  private static func pointsJson(
    face: [NormalizedLandmark],
    indexes: [Int]
  ) -> String {
    let points = indexes.compactMap { index -> String? in
      guard index >= 0 && index < face.count else {
        return nil
      }

      let landmark = face[index]
      let presence = landmark.presence?.floatValue ?? 1.0
      return """
      {"index":\(index),"x":\(format(landmark.x)),"y":\(format(landmark.y)),"z":\(format(landmark.z)),"presence":\(format(presence))}
      """
    }

    return "[\(points.joined(separator: ","))]"
  }

  private static func bboxJson(face: [NormalizedLandmark]) -> String {
    guard let first = face.first else {
      return "{\"left\":0,\"top\":0,\"right\":0,\"bottom\":0,\"width\":0,\"height\":0}"
    }

    var left = first.x
    var right = first.x
    var top = first.y
    var bottom = first.y

    for landmark in face {
      left = min(left, landmark.x)
      right = max(right, landmark.x)
      top = min(top, landmark.y)
      bottom = max(bottom, landmark.y)
    }

    return """
    {"left":\(format(left)),"top":\(format(top)),"right":\(format(right)),"bottom":\(format(bottom)),"width":\(format(right - left)),"height":\(format(bottom - top))}
    """
  }

  private static func averagePresence(
    face: [NormalizedLandmark],
    indexes: [Int]
  ) -> Float {
    var total: Float = 0
    var count: Float = 0

    for index in indexes where index >= 0 && index < face.count {
      total += face[index].presence?.floatValue ?? 1.0
      count += 1.0
    }

    return count > 0 ? total / count : 0
  }

  private static func failureJson(
    status: String,
    detail: String,
    imageWidth: Int32,
    imageHeight: Int32,
    startedAt: Date
  ) -> String {
    let latencyMs = Int(Date().timeIntervalSince(startedAt) * 1000.0)
    return """
    {"status":"\(escape(status))","detail":"\(escape(detail))","source":"\(source)","coordinateMode":"\(coordinateMode)","imageWidth":\(imageWidth),"imageHeight":\(imageHeight),"faceCount":0,"landmarkCount":0,"leftPointCount":0,"rightPointCount":0,"confidence":0,"latencyMs":\(latencyMs),"bbox":{"left":0,"top":0,"right":0,"bottom":0,"width":0,"height":0},"leftEyebrow":[],"rightEyebrow":[],"rawCameraFrameStored":false,"offDeviceUpload":false}
    """
  }

  private static func format(_ value: Float) -> String {
    String(format: "%.6f", value)
  }

  private static func escape(_ value: String) -> String {
    value
      .replacingOccurrences(of: "\\", with: "\\\\")
      .replacingOccurrences(of: "\"", with: "\\\"")
      .replacingOccurrences(of: "\n", with: "\\n")
      .replacingOccurrences(of: "\r", with: "\\r")
  }
}

@_cdecl("E7MediaPipeAppDetectFullFaceBgra")
public func E7MediaPipeAppDetectFullFaceBgra(
  _ bgraBytes: UnsafePointer<UInt8>?,
  _ byteCount: Int32,
  _ imageWidth: Int32,
  _ imageHeight: Int32,
  _ timestampMs: Int64,
  _ orientationDegrees: Int32
) -> UnsafeMutablePointer<CChar>? {
  let json = MakeupARMediaPipeFullFaceRuntime.detectFullFaceBgra(
    bytes: bgraBytes,
    byteCount: byteCount,
    imageWidth: imageWidth,
    imageHeight: imageHeight,
    timestampMs: timestampMs,
    orientationDegrees: orientationDegrees
  )
  return strdup(json)
}

@_cdecl("E7MediaPipeAppDetectFullFaceFromNativeFrame")
public func E7MediaPipeAppDetectFullFaceFromNativeFrame(
  _ frameHandle: Int64,
  _ timestampMs: Int64
) -> UnsafeMutablePointer<CChar>? {
  let json = MakeupARMediaPipeFullFaceRuntime.detectFullFaceNativeFrameNotConnected(
    frameHandle: frameHandle,
    timestampMs: timestampMs
  )
  return strdup(json)
}

@_cdecl("E7MediaPipeAppDetectBrowLandmarksPng")
public func E7MediaPipeAppDetectBrowLandmarksPng(
  _ pngBytes: UnsafePointer<UInt8>?,
  _ byteCount: Int32,
  _ imageWidth: Int32,
  _ imageHeight: Int32
) -> UnsafeMutablePointer<CChar>? {
  let json = MakeupARMediaPipeBrowRuntime.detectBrowLandmarksPng(
    bytes: pngBytes,
    byteCount: byteCount,
    imageWidth: imageWidth,
    imageHeight: imageHeight
  )
  return strdup(json)
}

@_cdecl("E7MediaPipeAppReleaseCString")
public func E7MediaPipeAppReleaseCString(_ pointer: UnsafeMutablePointer<CChar>?) {
  if let pointer {
    free(pointer)
  }
}
