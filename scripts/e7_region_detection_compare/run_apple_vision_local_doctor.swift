#!/usr/bin/env swift
import CoreGraphics
import Foundation
import ImageIO
import Vision

struct Options {
    var imagePath: String?
    var outputJson: String?
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
                throw NSError(domain: "E7VisionDoctor", code: 2, userInfo: [
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
        case "--help", "-h":
            print("""
            Usage:
              xcrun swift scripts/e7_region_detection_compare/run_apple_vision_local_doctor.swift \\
                --image path/to/frame.png \\
                --output-json path/to/vision_doctor.json
            """)
            Foundation.exit(0)
        default:
            throw NSError(domain: "E7VisionDoctor", code: 2, userInfo: [
                NSLocalizedDescriptionKey: "Unknown argument \(arg)"
            ])
        }
        index += 1
    }
    guard options.imagePath != nil else {
        throw NSError(domain: "E7VisionDoctor", code: 2, userInfo: [
            NSLocalizedDescriptionKey: "--image is required"
        ])
    }
    guard options.outputJson != nil else {
        throw NSError(domain: "E7VisionDoctor", code: 2, userInfo: [
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

func loadImage(_ url: URL) throws -> (CGImage, Int, Int) {
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil) else {
        throw NSError(domain: "E7VisionDoctor", code: 3, userInfo: [
            NSLocalizedDescriptionKey: "Could not create image source"
        ])
    }
    guard let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        throw NSError(domain: "E7VisionDoctor", code: 3, userInfo: [
            NSLocalizedDescriptionKey: "Could not decode image"
        ])
    }
    return (image, image.width, image.height)
}

func orientationLabel(_ orientation: CGImagePropertyOrientation) -> String {
    switch orientation {
    case .up: return "up"
    case .down: return "down"
    case .left: return "left"
    case .right: return "right"
    case .upMirrored: return "upMirrored"
    case .downMirrored: return "downMirrored"
    case .leftMirrored: return "leftMirrored"
    case .rightMirrored: return "rightMirrored"
    @unknown default: return "unknown"
    }
}

func runRectangleProbe(image: CGImage, orientation: CGImagePropertyOrientation) -> [String: Any] {
    let request = VNDetectFaceRectanglesRequest()
    let handler = VNImageRequestHandler(cgImage: image, orientation: orientation, options: [:])
    do {
        try handler.perform([request])
        return [
            "status": "completed",
            "faceObservationCount": request.results?.count ?? 0
        ]
    } catch {
        return [
            "status": "request_failed",
            "error": error.localizedDescription
        ]
    }
}

func runDirectLandmarkProbe(image: CGImage, orientation: CGImagePropertyOrientation) -> [String: Any] {
    let request = VNDetectFaceLandmarksRequest()
    let handler = VNImageRequestHandler(cgImage: image, orientation: orientation, options: [:])
    do {
        try handler.perform([request])
        let face = request.results?.first
        return [
            "status": "completed",
            "faceObservationCount": request.results?.count ?? 0,
            "hasLandmarks": face?.landmarks != nil,
            "leftEyePointCount": face?.landmarks?.leftEye?.pointCount ?? 0,
            "rightEyePointCount": face?.landmarks?.rightEye?.pointCount ?? 0,
            "leftEyebrowPointCount": face?.landmarks?.leftEyebrow?.pointCount ?? 0,
            "rightEyebrowPointCount": face?.landmarks?.rightEyebrow?.pointCount ?? 0
        ]
    } catch {
        return [
            "status": "request_failed",
            "error": error.localizedDescription
        ]
    }
}

func runRectangleThenLandmarkProbe(image: CGImage, orientation: CGImagePropertyOrientation) -> [String: Any] {
    let rectangleRequest = VNDetectFaceRectanglesRequest()
    let rectangleHandler = VNImageRequestHandler(cgImage: image, orientation: orientation, options: [:])
    do {
        try rectangleHandler.perform([rectangleRequest])
    } catch {
        return [
            "status": "rectangle_request_failed",
            "error": error.localizedDescription
        ]
    }

    let faces = rectangleRequest.results ?? []
    guard !faces.isEmpty else {
        return [
            "status": "no_rectangle_faces",
            "faceObservationCount": 0
        ]
    }

    let landmarkRequest = VNDetectFaceLandmarksRequest()
    landmarkRequest.inputFaceObservations = faces
    let landmarkHandler = VNImageRequestHandler(cgImage: image, orientation: orientation, options: [:])
    do {
        try landmarkHandler.perform([landmarkRequest])
        let face = landmarkRequest.results?.first
        return [
            "status": "completed",
            "rectangleFaceObservationCount": faces.count,
            "landmarkFaceObservationCount": landmarkRequest.results?.count ?? 0,
            "hasLandmarks": face?.landmarks != nil,
            "leftEyePointCount": face?.landmarks?.leftEye?.pointCount ?? 0,
            "rightEyePointCount": face?.landmarks?.rightEye?.pointCount ?? 0,
            "leftEyebrowPointCount": face?.landmarks?.leftEyebrow?.pointCount ?? 0,
            "rightEyebrowPointCount": face?.landmarks?.rightEyebrow?.pointCount ?? 0
        ]
    } catch {
        return [
            "status": "landmark_request_failed",
            "rectangleFaceObservationCount": faces.count,
            "error": error.localizedDescription
        ]
    }
}

func main() throws {
    let options = try parseOptions()
    let imageUrl = URL(fileURLWithPath: options.imagePath!)
    let outputUrl = URL(fileURLWithPath: options.outputJson!)
    try FileManager.default.createDirectory(
        at: outputUrl.deletingLastPathComponent(),
        withIntermediateDirectories: true
    )
    let (image, width, height) = try loadImage(imageUrl)
    let orientations: [CGImagePropertyOrientation] = [.up, .right, .left, .down]
    var probes: [[String: Any]] = []

    for orientation in orientations {
        probes.append([
            "orientation": orientationLabel(orientation),
            "faceRectangles": runRectangleProbe(image: image, orientation: orientation),
            "directLandmarks": runDirectLandmarkProbe(image: image, orientation: orientation),
            "rectanglesThenLandmarks": runRectangleThenLandmarkProbe(image: image, orientation: orientation)
        ])
    }

    let result: [String: Any] = [
        "schemaVersion": "e7-apple-vision-local-doctor-v0",
        "createdAt": utcNow(),
        "sourceFramePath": imageUrl.path,
        "image": [
            "width": width,
            "height": height
        ],
        "probes": probes,
        "privacy": [
            "localOnly": true,
            "offDeviceUpload": false,
            "rawFrameStoredByThisTool": false
        ]
    ]
    let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
    try data.write(to: outputUrl)
}

do {
    try main()
} catch {
    FileHandle.standardError.write(Data("E7VisionDoctor error: \(error.localizedDescription)\n".utf8))
    Foundation.exit(1)
}
