import Foundation
import ImageIO
import React
import UIKit
import Vision

#if canImport(MediaPipeTasksVision)
import MediaPipeTasksVision
#endif

@objc(E7NativeLipBoundaryProviders)
final class E7NativeLipBoundaryProviders: NSObject {
  @objc
  static func requiresMainQueueSetup() -> Bool {
    false
  }

  @objc(extractLipBoundary:resolver:rejecter:)
  func extractLipBoundary(
    _ requestJson: String,
    resolver resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    do {
      let request = try parseRequest(requestJson)
      if request.provider == "mediapipe" {
        resolve(try extractMediaPipeBoundary(request))
        return
      }

      let frameUrl = try resolveAppFilePath(request.framePath)
      let exportUrl = try resolveAppFilePath(request.arFaceExportPath)
      let imageSource = CGImageSourceCreateWithURL(frameUrl as CFURL, nil)
      guard let imageSource,
            let cgImage = CGImageSourceCreateImageAtIndex(imageSource, 0, nil) else {
        throw E7NativeProviderError.invalidFrameImage(request.framePath)
      }

      let landmarks = try extractVisionLipLandmarks(
        cgImage: cgImage,
        orientation: request.orientation
      )
      let arFaceExport = try readJsonObject(exportUrl)
      let result: [String: Any] = [
        "status": landmarks.outerPoints.count >= 3 ? "ready" : "blocked",
        "provider": "vision",
        "captureSetId": request.captureSetId,
        "capturePairId": request.capturePairId,
        "captureShotKind": request.captureShotKind,
        "framePath": request.framePath,
        "framePreviewUri": frameUrl.absoluteString,
        "arFaceExportPath": request.arFaceExportPath,
        "frameWidth": cgImage.width,
        "frameHeight": cgImage.height,
        "boundary": [
          "coordinateSpace": "frame_image_pixel_top_left",
          "outerPoints": landmarks.outerPoints,
          "innerPoints": landmarks.innerPoints,
          "source": "vision",
          "generationMethod": "native_vision_curve_landmarks"
        ],
        "arFaceExport": arFaceExport,
        "blendShapes": arFaceExport["blendShapes"] as? [String: Any] ?? [
          "available": false,
          "reason": "blendShapes_missing_from_arface_export"
        ],
        "warnings": [
          "native_vision_current_frame",
          "uv_projection_runs_in_rn_js_once_per_generate"
        ]
      ]
      resolve(try jsonString(result))
    } catch {
      reject(
        "E7_NATIVE_PROVIDER_FAILED",
        error.localizedDescription,
        error
      )
    }
  }

  private func extractMediaPipeBoundary(_ request: E7NativeBoundaryRequest) throws -> String {
    let frameUrl = try resolveAppFilePath(request.framePath)
    let exportUrl = try resolveAppFilePath(request.arFaceExportPath)
    let imageSource = CGImageSourceCreateWithURL(frameUrl as CFURL, nil)
    guard let imageSource,
          let cgImage = CGImageSourceCreateImageAtIndex(imageSource, 0, nil) else {
      throw E7NativeProviderError.invalidFrameImage(request.framePath)
    }
    let arFaceExport = try readJsonObject(exportUrl)

    #if canImport(MediaPipeTasksVision)
    let landmarks = try extractMediaPipeLipLandmarks(
      frameUrl: frameUrl,
      width: cgImage.width,
      height: cgImage.height
    )
    let result: [String: Any] = [
      "status": landmarks.outerPoints.count >= 3 ? "ready" : "blocked",
      "provider": "mediapipe",
      "captureSetId": request.captureSetId,
      "capturePairId": request.capturePairId,
      "captureShotKind": request.captureShotKind,
      "framePath": request.framePath,
      "framePreviewUri": frameUrl.absoluteString,
      "arFaceExportPath": request.arFaceExportPath,
      "frameWidth": cgImage.width,
      "frameHeight": cgImage.height,
      "boundary": [
        "coordinateSpace": "frame_image_pixel_top_left",
        "outerPoints": landmarks.outerPoints,
        "innerPoints": landmarks.innerPoints,
        "source": "mediapipe",
        "generationMethod": "native_mediapipe_face_landmarker_curve"
      ],
      "arFaceExport": arFaceExport,
      "blendShapes": arFaceExport["blendShapes"] as? [String: Any] ?? [
        "available": false,
        "reason": "blendShapes_missing_from_arface_export"
      ],
      "warnings": [
        "native_mediapipe_current_frame",
        "uv_projection_runs_in_rn_js_once_per_generate"
      ]
    ]
    return try jsonString(result)
    #else
    return try jsonString([
      "status": "blocked",
      "provider": "mediapipe",
      "captureSetId": request.captureSetId,
      "capturePairId": request.capturePairId,
      "captureShotKind": request.captureShotKind,
      "framePath": request.framePath,
      "framePreviewUri": frameUrl.absoluteString,
      "arFaceExportPath": request.arFaceExportPath,
      "frameWidth": cgImage.width,
      "frameHeight": cgImage.height,
      "arFaceExport": arFaceExport,
      "warnings": [
        "native_mediapipe_provider_called_current_frame",
        "mediapipe_tasks_vision_module_not_installed"
      ],
      "blockedReason": "mediapipe_tasks_vision_module_not_installed"
    ])
    #endif
  }

  @objc(saveGeneratedPackage:resolver:rejecter:)
  func saveGeneratedPackage(
    _ packageJson: String,
    resolver resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    do {
      guard let data = packageJson.data(using: .utf8),
            let package = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
        throw E7NativeProviderError.invalidPackageJson
      }
      let generatedMaskId =
        sanitizePathComponent(package["generatedMaskId"] as? String ?? "generated-lip-mask")
      let root = try documentsDirectory()
        .appendingPathComponent("e7-generated-lip-packages", isDirectory: true)
        .appendingPathComponent(generatedMaskId, isDirectory: true)
      try FileManager.default.createDirectory(
        at: root,
        withIntermediateDirectories: true
      )
      let packageUrl = root.appendingPathComponent("generated_lip_package.json")
      try data.write(to: packageUrl, options: .atomic)

      let record: [String: Any] = [
        "schemaVersion": "e7-lip-generate-saved-record-v0",
        "savedAt": isoNow(),
        "generatedMaskId": generatedMaskId,
        "provider": package["provider"] as? String ?? "unknown",
        "expressionMode": package["expressionMode"] as? String ?? "unknown",
        "status": "saved_local_only",
        "packagePath": packageUrl.path,
        "runtimeReady": false,
        "privacyFlags": [
          "localOnly": true,
          "offDeviceUpload": false,
          "longTermRawFrameStored": false
        ]
      ]
      let recordUrl = root.appendingPathComponent("saved_record.json")
      try jsonData(record).write(to: recordUrl, options: .atomic)
      resolve(try jsonString(record.merging(["metadataPath": recordUrl.path]) { _, new in new }))
    } catch {
      reject(
        "E7_SAVE_PACKAGE_FAILED",
        error.localizedDescription,
        error
      )
    }
  }

  private func parseRequest(_ json: String) throws -> E7NativeBoundaryRequest {
    guard let data = json.data(using: .utf8),
          let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
      throw E7NativeProviderError.invalidRequestJson
    }
    let provider = object["provider"] as? String ?? "vision"
    let captureSetId = object["captureSetId"] as? String ?? "capture-set"
    let capturePairId = object["capturePairId"] as? String ?? "pair_face_unknown"
    let captureShotKind = object["captureShotKind"] as? String ?? "neutral"
    let framePath = object["framePath"] as? String ?? ""
    let arFaceExportPath = object["arFaceExportPath"] as? String ?? ""
    if framePath.isEmpty {
      throw E7NativeProviderError.missingField("framePath")
    }
    if arFaceExportPath.isEmpty {
      throw E7NativeProviderError.missingField("arFaceExportPath")
    }
    return E7NativeBoundaryRequest(
      provider: provider,
      captureSetId: captureSetId,
      capturePairId: capturePairId,
      captureShotKind: captureShotKind,
      framePath: framePath,
      arFaceExportPath: arFaceExportPath,
      orientation: object["orientation"] as? String ?? "up"
    )
  }

  private func resolveAppFilePath(_ value: String) throws -> URL {
    let fileUrl = URL(fileURLWithPath: value)
    if fileUrl.isFileURL, FileManager.default.fileExists(atPath: fileUrl.path) {
      return fileUrl
    }

    let documents = try documentsDirectory()
    let trimmed = value
      .replacingOccurrences(of: "Documents/", with: "")
      .trimmingCharacters(in: CharacterSet(charactersIn: "/"))
    let url = documents.appendingPathComponent(trimmed)
    if FileManager.default.fileExists(atPath: url.path) {
      return url
    }
    throw E7NativeProviderError.fileNotFound(value)
  }

  private func documentsDirectory() throws -> URL {
    guard let url = FileManager.default.urls(
      for: .documentDirectory,
      in: .userDomainMask
    ).first else {
      throw E7NativeProviderError.documentsDirectoryUnavailable
    }
    return url
  }

  private func readJsonObject(_ url: URL) throws -> [String: Any] {
    let data = try Data(contentsOf: url)
    guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
      throw E7NativeProviderError.invalidArFaceExport(url.path)
    }
    return object
  }

  private func extractVisionLipLandmarks(
    cgImage: CGImage,
    orientation: String
  ) throws -> E7VisionLipLandmarks {
    let request = VNDetectFaceLandmarksRequest()
    let handler = VNImageRequestHandler(
      cgImage: cgImage,
      orientation: cgImageOrientation(orientation),
      options: [:]
    )
    try handler.perform([request])
    guard let face = request.results?.first,
          let landmarks = face.landmarks,
          let outerLips = landmarks.outerLips else {
      throw E7NativeProviderError.visionLipLandmarksMissing
    }

    return E7VisionLipLandmarks(
      outerPoints: convertLandmarkPoints(
        outerLips,
        faceBoundingBox: face.boundingBox,
        width: cgImage.width,
        height: cgImage.height
      ),
      innerPoints: convertLandmarkPoints(
        landmarks.innerLips,
        faceBoundingBox: face.boundingBox,
        width: cgImage.width,
        height: cgImage.height
      )
    )
  }

  #if canImport(MediaPipeTasksVision)
  private func extractMediaPipeLipLandmarks(
    frameUrl: URL,
    width: Int,
    height: Int
  ) throws -> E7MediaPipeLipLandmarks {
    guard let modelPath = Bundle.main.path(
      forResource: "face_landmarker",
      ofType: "task"
    ) else {
      throw E7NativeProviderError.mediapipeModelMissing
    }
    guard let uiImage = UIImage(contentsOfFile: frameUrl.path) else {
      throw E7NativeProviderError.invalidFrameImage(frameUrl.path)
    }

    let options = FaceLandmarkerOptions()
    options.baseOptions.modelAssetPath = modelPath
    options.runningMode = .image
    options.numFaces = 1
    options.outputFaceBlendshapes = false
    options.outputFacialTransformationMatrixes = false
    options.minFaceDetectionConfidence = 0.3
    options.minFacePresenceConfidence = 0.3
    options.minTrackingConfidence = 0.3

    let landmarker = try FaceLandmarker(options: options)
    let image = try MPImage(uiImage: uiImage)
    let result = try landmarker.detect(image: image)
    guard let faceLandmarks = result.faceLandmarks.first else {
      throw E7NativeProviderError.mediapipeNoFaceDetected
    }

    let requiredIndex = max(
      mediaPipeOuterLipIndices.max() ?? 0,
      mediaPipeInnerLipIndices.max() ?? 0
    )
    if faceLandmarks.count <= requiredIndex {
      throw E7NativeProviderError.mediapipeLandmarkCountTooSmall(
        faceLandmarks.count,
        requiredIndex
      )
    }

    return E7MediaPipeLipLandmarks(
      outerPoints: convertMediaPipePoints(
        faceLandmarks,
        indices: mediaPipeOuterLipIndices,
        width: width,
        height: height
      ),
      innerPoints: convertMediaPipePoints(
        faceLandmarks,
        indices: mediaPipeInnerLipIndices,
        width: width,
        height: height
      )
    )
  }

  private func convertMediaPipePoints(
    _ landmarks: [NormalizedLandmark],
    indices: [Int],
    width: Int,
    height: Int
  ) -> [[String: Double]] {
    indices.map { index in
      let landmark = landmarks[index]
      return [
        "x": Double(landmark.x) * Double(width),
        "y": Double(landmark.y) * Double(height),
        "z": Double(landmark.z)
      ]
    }
  }
  #endif

  private func convertLandmarkPoints(
    _ region: VNFaceLandmarkRegion2D?,
    faceBoundingBox: CGRect,
    width: Int,
    height: Int
  ) -> [[String: Double]] {
    guard let region else {
      return []
    }
    return region.normalizedPoints.map { point in
      let normalizedX = faceBoundingBox.minX + CGFloat(point.x) * faceBoundingBox.width
      let normalizedY = faceBoundingBox.minY + CGFloat(point.y) * faceBoundingBox.height
      return [
        "x": Double(normalizedX * CGFloat(width)),
        "y": Double((1.0 - normalizedY) * CGFloat(height))
      ]
    }
  }

  private func cgImageOrientation(_ value: String) -> CGImagePropertyOrientation {
    switch value {
    case "upMirrored":
      return .upMirrored
    case "down":
      return .down
    case "downMirrored":
      return .downMirrored
    case "left":
      return .left
    case "leftMirrored":
      return .leftMirrored
    case "right":
      return .right
    case "rightMirrored":
      return .rightMirrored
    default:
      return .up
    }
  }

  private func jsonString(_ object: Any) throws -> String {
    String(data: try jsonData(object), encoding: .utf8) ?? "{}"
  }

  private func jsonData(_ object: Any) throws -> Data {
    try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
  }

  private func sanitizePathComponent(_ value: String) -> String {
    let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "._-"))
    let filtered = value.unicodeScalars.map { scalar in
      allowed.contains(scalar) ? String(scalar) : "-"
    }.joined()
    return filtered.trimmingCharacters(in: CharacterSet(charactersIn: ".-"))
  }

  private func isoNow() -> String {
    let formatter = ISO8601DateFormatter()
    formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    return formatter.string(from: Date())
  }
}

private struct E7NativeBoundaryRequest {
  let provider: String
  let captureSetId: String
  let capturePairId: String
  let captureShotKind: String
  let framePath: String
  let arFaceExportPath: String
  let orientation: String
}

private struct E7VisionLipLandmarks {
  let outerPoints: [[String: Double]]
  let innerPoints: [[String: Double]]
}

private struct E7MediaPipeLipLandmarks {
  let outerPoints: [[String: Double]]
  let innerPoints: [[String: Double]]
}

private let mediaPipeOuterLipIndices = [
  61, 146, 91, 181, 84, 17, 314, 405, 321, 375,
  291, 409, 270, 269, 267, 0, 37, 39, 40, 185
]

private let mediaPipeInnerLipIndices = [
  78, 95, 88, 178, 87, 14, 317, 402, 318, 324,
  308, 415, 310, 311, 312, 13, 82, 81, 80, 191
]

private enum E7NativeProviderError: LocalizedError {
  case invalidRequestJson
  case invalidPackageJson
  case missingField(String)
  case fileNotFound(String)
  case invalidFrameImage(String)
  case invalidArFaceExport(String)
  case documentsDirectoryUnavailable
  case visionLipLandmarksMissing
  case mediapipeModelMissing
  case mediapipeNoFaceDetected
  case mediapipeLandmarkCountTooSmall(Int, Int)

  var errorDescription: String? {
    switch self {
    case .invalidRequestJson:
      return "Invalid native boundary request JSON."
    case .invalidPackageJson:
      return "Invalid generated package JSON."
    case .missingField(let field):
      return "Missing required field: \(field)."
    case .fileNotFound(let path):
      return "Capture file not found: \(path)."
    case .invalidFrameImage(let path):
      return "Frame image could not be decoded: \(path)."
    case .invalidArFaceExport(let path):
      return "ARFace export JSON could not be decoded: \(path)."
    case .documentsDirectoryUnavailable:
      return "Documents directory is unavailable."
    case .visionLipLandmarksMissing:
      return "Vision did not return lip landmarks for the current frame."
    case .mediapipeModelMissing:
      return "MediaPipe face_landmarker.task is not bundled in the app resources."
    case .mediapipeNoFaceDetected:
      return "MediaPipe did not detect a face for the current frame."
    case .mediapipeLandmarkCountTooSmall(let count, let requiredIndex):
      return "MediaPipe returned \(count) landmarks; required index \(requiredIndex)."
    }
  }
}
