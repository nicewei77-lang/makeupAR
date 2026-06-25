#!/usr/bin/env swift
import CoreGraphics
import CryptoKit
import Foundation
import ImageIO
import Vision

struct Options {
    var imagePath: String?
    var outputJson: String?
    var capturePairId: String?
    var minConfidence: Float = 0.35
}

func parseOptions() throws -> Options {
    var options = Options()
    var index = 1
    let args = CommandLine.arguments
    while index < args.count {
        let arg = args[index]
        func requireValue() throws -> String {
            let valueIndex = index + 1
            guard valueIndex < args.count else {
                throw NSError(domain: "AppleVisionLipContour", code: 2, userInfo: [
                    NSLocalizedDescriptionKey: "Missing value for \(arg)"
                ])
            }
            index += 1
            return args[valueIndex]
        }

        switch arg {
        case "--image":
            options.imagePath = try requireValue()
        case "--output-json":
            options.outputJson = try requireValue()
        case "--capture-pair-id":
            options.capturePairId = try requireValue()
        case "--min-confidence":
            let raw = try requireValue()
            options.minConfidence = Float(raw) ?? options.minConfidence
        case "--help", "-h":
            print("""
            Usage:
              xcrun swift scripts/e7_lip_boundary_fusion/extract_apple_vision_lip_contour.swift \\
                --image path/to/frame.png \\
                --output-json path/to/apple_vision_lip_contour.json \\
                [--capture-pair-id pair_id] [--min-confidence 0.35]
            """)
            Foundation.exit(0)
        default:
            throw NSError(domain: "AppleVisionLipContour", code: 2, userInfo: [
                NSLocalizedDescriptionKey: "Unknown argument \(arg)"
            ])
        }
        index += 1
    }
    guard options.imagePath != nil else {
        throw NSError(domain: "AppleVisionLipContour", code: 2, userInfo: [
            NSLocalizedDescriptionKey: "--image is required"
        ])
    }
    guard options.outputJson != nil else {
        throw NSError(domain: "AppleVisionLipContour", code: 2, userInfo: [
            NSLocalizedDescriptionKey: "--output-json is required"
        ])
    }
    return options
}

func utcNow() -> String {
    let formatter = ISO8601DateFormatter()
    formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    return formatter.string(from: Date())
}

func sha256Hex(_ url: URL) throws -> String {
    let data = try Data(contentsOf: url)
    let digest = SHA256.hash(data: data)
    return digest.map { String(format: "%02x", $0) }.joined()
}

func round6(_ value: CGFloat) -> Double {
    return (Double(value) * 1_000_000).rounded() / 1_000_000
}

func round3(_ value: CGFloat) -> Double {
    return (Double(value) * 1_000).rounded() / 1_000
}

func loadImage(_ url: URL) throws -> (CGImage, Int, Int) {
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil) else {
        throw NSError(domain: "AppleVisionLipContour", code: 3, userInfo: [
            NSLocalizedDescriptionKey: "Could not create image source"
        ])
    }
    guard let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        throw NSError(domain: "AppleVisionLipContour", code: 3, userInfo: [
            NSLocalizedDescriptionKey: "Could not decode image"
        ])
    }
    return (image, image.width, image.height)
}

func imagePoint(from point: CGPoint, faceBoundingBox: CGRect, width: Int, height: Int) -> [String: Double] {
    let normalizedX = faceBoundingBox.origin.x + point.x * faceBoundingBox.size.width
    let normalizedYBottomLeft = faceBoundingBox.origin.y + point.y * faceBoundingBox.size.height
    let pixelX = normalizedX * CGFloat(width)
    let pixelY = (1.0 - normalizedYBottomLeft) * CGFloat(height)
    return ["x": round3(pixelX), "y": round3(pixelY)]
}

func normalizedPoint(_ point: CGPoint) -> [String: Double] {
    return ["x": round6(point.x), "y": round6(point.y)]
}

func bounds(_ points: [[String: Double]]) -> [String: Any]? {
    guard !points.isEmpty else { return nil }
    let xs = points.compactMap { $0["x"] }
    let ys = points.compactMap { $0["y"] }
    guard let minX = xs.min(), let maxX = xs.max(), let minY = ys.min(), let maxY = ys.max() else {
        return nil
    }
    return [
        "minX": minX,
        "minY": minY,
        "maxX": maxX,
        "maxY": maxY,
        "width": ((maxX - minX) * 1_000).rounded() / 1_000,
        "height": ((maxY - minY) * 1_000).rounded() / 1_000
    ]
}

func contourDict(
    _ region: VNFaceLandmarkRegion2D?,
    faceBoundingBox: CGRect,
    width: Int,
    height: Int
) -> [String: Any] {
    guard let region else {
        return ["status": "unavailable", "pointCount": 0]
    }
    let normalized = region.normalizedPoints.map { normalizedPoint($0) }
    let imagePoints = region.normalizedPoints.map {
        imagePoint(from: $0, faceBoundingBox: faceBoundingBox, width: width, height: height)
    }
    return [
        "status": imagePoints.isEmpty ? "unavailable" : "available",
        "pointCount": imagePoints.count,
        "normalizedFaceBoundingBoxPoints": normalized,
        "imagePoints": imagePoints,
        "imageBounds": bounds(imagePoints) as Any
    ]
}

func unavailableResult(
    imageUrl: URL,
    options: Options,
    width: Int?,
    height: Int?,
    reason: String
) -> [String: Any] {
    return [
        "schemaVersion": "e7-apple-vision-lip-contour-v0",
        "createdAtUtc": utcNow(),
        "status": "unavailable",
        "unavailableReason": reason,
        "capturePairId": options.capturePairId as Any,
        "sourceFramePath": imageUrl.path,
        "sourceFrameSha256": (try? sha256Hex(imageUrl)) as Any,
        "image": [
            "width": width as Any,
            "height": height as Any,
            "orientationAssumption": "cgImagePropertyOrientationUp"
        ],
        "request": [
            "framework": "Apple Vision",
            "request": "VNDetectFaceLandmarksRequest",
            "runtimeUse": "calibration_offline_only"
        ],
        "requiredForM1Ready": true,
        "privacy": [
            "localOnly": true,
            "offDeviceUpload": false,
            "rawFrameStoredByThisTool": false
        ]
    ]
}

func main() throws {
    let options = try parseOptions()
    let imageUrl = URL(fileURLWithPath: options.imagePath!)
    let outputUrl = URL(fileURLWithPath: options.outputJson!)

    let image: CGImage
    let width: Int
    let height: Int
    do {
        (image, width, height) = try loadImage(imageUrl)
    } catch {
        let result = unavailableResult(
            imageUrl: imageUrl,
            options: options,
            width: nil,
            height: nil,
            reason: "image_decode_failed:\(error.localizedDescription)"
        )
        let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: outputUrl)
        return
    }

    let request = VNDetectFaceLandmarksRequest()
    let handler = VNImageRequestHandler(cgImage: image, orientation: .up, options: [:])
    do {
        try handler.perform([request])
    } catch {
        let result = unavailableResult(
            imageUrl: imageUrl,
            options: options,
            width: width,
            height: height,
            reason: "vision_request_failed:\(error.localizedDescription)"
        )
        let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: outputUrl)
        return
    }

    let observations = request.results ?? []
    guard let face = observations.max(by: { $0.confidence < $1.confidence }) else {
        let result = unavailableResult(
            imageUrl: imageUrl,
            options: options,
            width: width,
            height: height,
            reason: "no_face_observation"
        )
        let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: outputUrl)
        return
    }

    guard let landmarks = face.landmarks else {
        let result = unavailableResult(
            imageUrl: imageUrl,
            options: options,
            width: width,
            height: height,
            reason: "face_landmarks_unavailable"
        )
        let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: outputUrl)
        return
    }

    let outer = contourDict(landmarks.outerLips, faceBoundingBox: face.boundingBox, width: width, height: height)
    let inner = contourDict(landmarks.innerLips, faceBoundingBox: face.boundingBox, width: width, height: height)
    let outerCount = outer["pointCount"] as? Int ?? 0
    let innerCount = inner["pointCount"] as? Int ?? 0
    let hasContours = outerCount > 0 || innerCount > 0
    let confidence = face.confidence
    let status = hasContours && confidence >= options.minConfidence ? "available" : "low_confidence"

    let bbox = face.boundingBox
    let result: [String: Any] = [
        "schemaVersion": "e7-apple-vision-lip-contour-v0",
        "createdAtUtc": utcNow(),
        "status": status,
        "capturePairId": options.capturePairId as Any,
        "sourceFramePath": imageUrl.path,
        "sourceFrameSha256": try sha256Hex(imageUrl),
        "image": [
            "width": width,
            "height": height,
            "orientationAssumption": "cgImagePropertyOrientationUp"
        ],
        "request": [
            "framework": "Apple Vision",
            "request": "VNDetectFaceLandmarksRequest",
            "runtimeUse": "calibration_offline_only",
            "minConfidenceForAvailable": options.minConfidence
        ],
        "coordinateSpaces": [
            "visionLandmarks": "face_bbox_normalized_bottom_left",
            "imagePoints": "frame_image_pixel_top_left"
        ],
        "confidence": Double(confidence),
        "faceObservationCount": observations.count,
        "selectedFace": [
            "confidence": Double(confidence),
            "boundingBoxNormalizedBottomLeft": [
                "x": round6(bbox.origin.x),
                "y": round6(bbox.origin.y),
                "width": round6(bbox.size.width),
                "height": round6(bbox.size.height)
            ]
        ],
        "contours": [
            "outerLips": outer,
            "innerLips": inner
        ],
        "requiredForM1Ready": true,
        "privacy": [
            "localOnly": true,
            "offDeviceUpload": false,
            "rawFrameStoredByThisTool": false
        ],
        "limits": [
            "twoDimensionalContourOnly": true,
            "notRuntimePrimaryTracker": true,
            "doesNotCreateGoldMask": true,
            "mustBeComparedWithARFaceProjectionAndHumanOrSilverReference": true
        ]
    ]

    let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
    try data.write(to: outputUrl)
}

do {
    try main()
} catch {
    fputs("extract_apple_vision_lip_contour.swift: \(error.localizedDescription)\n", stderr)
    Foundation.exit(1)
}
