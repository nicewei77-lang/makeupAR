#!/usr/bin/env swift

import CoreGraphics
import Foundation
import ImageIO
import Vision

let arguments = Array(CommandLine.arguments.dropFirst())
var outputPath = ""
var inputPaths: [String] = []
var index = 0

while index < arguments.count {
    let argument = arguments[index]
    switch argument {
    case "--out":
        index += 1
        guard index < arguments.count else {
            fatalError("--out requires a path")
        }
        outputPath = arguments[index]
    case "--help", "-h":
        print("""
        Usage:
          swift scripts/e7_reference_atlas/run_vision_face_landmark_dump.swift \\
            --out evidence/e7-reference-atlas/cheek-vision-reference/landmarks.json \\
            image1.png image2.png

        Dumps Apple Vision face bounding boxes and 2D landmark points in the
        same raw-y image coordinate mode validated by the E7 lip Vision gate.
        """)
        exit(0)
    default:
        inputPaths.append(argument)
    }
    index += 1
}

guard !outputPath.isEmpty else {
    fatalError("--out is required")
}
guard !inputPaths.isEmpty else {
    fatalError("At least one image path is required")
}

let outputURL = URL(fileURLWithPath: outputPath)
try FileManager.default.createDirectory(
    at: outputURL.deletingLastPathComponent(),
    withIntermediateDirectories: true)

var records: [[String: Any]] = []
for inputPath in inputPaths {
    do {
        records.append(try processImage(inputPath))
        print("vision_face_landmark_dump status=ok input=\(inputPath)")
    } catch {
        records.append([
            "inputPath": inputPath,
            "status": "error",
            "error": String(describing: error),
        ])
        print("vision_face_landmark_dump status=error input=\(inputPath) error=\(error)")
    }
}

let root: [String: Any] = [
    "gateId": "vision-cheek-reference-landmarks-v1",
    "source": "apple_vision_offline_face_landmarks",
    "coordinateMode": "raw-y",
    "rawCameraFrameStored": false,
    "offDeviceUpload": false,
    "images": records,
]
let data = try JSONSerialization.data(withJSONObject: root, options: [.prettyPrinted, .sortedKeys])
try data.write(to: outputURL)

func processImage(_ inputPath: String) throws -> [String: Any] {
    let inputURL = URL(fileURLWithPath: inputPath)
    guard let image = loadCGImage(inputURL) else {
        throw RuntimeError("could not load image")
    }

    let request = VNDetectFaceLandmarksRequest()
    request.usesCPUOnly = true
    let handler = VNImageRequestHandler(cgImage: image, orientation: .up, options: [:])
    try handler.perform([request])

    let faces = request.results ?? []
    let faceRecords = faces.enumerated().map { faceIndex, face in
        faceRecord(index: faceIndex, face: face, width: image.width, height: image.height)
    }

    return [
        "inputPath": inputPath,
        "status": "ok",
        "width": image.width,
        "height": image.height,
        "faceCount": faces.count,
        "faces": faceRecords,
    ]
}

func faceRecord(index: Int, face: VNFaceObservation, width: Int, height: Int) -> [String: Any] {
    var record: [String: Any] = [
        "index": index,
        "confidence": Double(face.confidence),
        "bbox": bboxRecord(face.boundingBox, width: width, height: height),
    ]

    guard let landmarks = face.landmarks else {
        record["landmarks"] = [:]
        return record
    }

    var landmarkRecords: [String: Any] = [:]
    addLandmark(&landmarkRecords, name: "faceContour", region: landmarks.faceContour, width: width, height: height)
    addLandmark(&landmarkRecords, name: "leftEye", region: landmarks.leftEye, width: width, height: height)
    addLandmark(&landmarkRecords, name: "rightEye", region: landmarks.rightEye, width: width, height: height)
    addLandmark(&landmarkRecords, name: "leftEyebrow", region: landmarks.leftEyebrow, width: width, height: height)
    addLandmark(&landmarkRecords, name: "rightEyebrow", region: landmarks.rightEyebrow, width: width, height: height)
    addLandmark(&landmarkRecords, name: "nose", region: landmarks.nose, width: width, height: height)
    addLandmark(&landmarkRecords, name: "noseCrest", region: landmarks.noseCrest, width: width, height: height)
    addLandmark(&landmarkRecords, name: "medianLine", region: landmarks.medianLine, width: width, height: height)
    addLandmark(&landmarkRecords, name: "outerLips", region: landmarks.outerLips, width: width, height: height)
    addLandmark(&landmarkRecords, name: "innerLips", region: landmarks.innerLips, width: width, height: height)
    record["landmarks"] = landmarkRecords
    return record
}

func addLandmark(
    _ output: inout [String: Any],
    name: String,
    region: VNFaceLandmarkRegion2D?,
    width: Int,
    height: Int) {
    guard let region = region else {
        return
    }
    let points = region.pointsInImage(imageSize: CGSize(width: width, height: height)).map { point in
        [
            "x": round3(Double(point.x)),
            "y": round3(Double(point.y)),
        ]
    }
    output[name] = [
        "pointCount": region.pointCount,
        "points": points,
        "bbox": pointBbox(points),
    ]
}

func bboxRecord(_ bbox: CGRect, width: Int, height: Int) -> [String: Any] {
    let left = Double(bbox.minX) * Double(width)
    let bottom = Double(bbox.minY) * Double(height)
    let right = Double(bbox.maxX) * Double(width)
    let top = Double(bbox.maxY) * Double(height)
    return [
        "left": round3(left),
        "bottom": round3(bottom),
        "right": round3(right),
        "top": round3(top),
        "width": round3(right - left),
        "height": round3(top - bottom),
        "centerX": round3((left + right) * 0.5),
        "centerY": round3((bottom + top) * 0.5),
    ]
}

func pointBbox(_ points: [[String: Double]]) -> [String: Any] {
    let xs = points.compactMap { $0["x"] }
    let ys = points.compactMap { $0["y"] }
    guard let left = xs.min(), let right = xs.max(), let bottom = ys.min(), let top = ys.max() else {
        return [:]
    }
    return [
        "left": round3(left),
        "bottom": round3(bottom),
        "right": round3(right),
        "top": round3(top),
        "width": round3(right - left),
        "height": round3(top - bottom),
        "centerX": round3((left + right) * 0.5),
        "centerY": round3((bottom + top) * 0.5),
    ]
}

func round3(_ value: Double) -> Double {
    (value * 1000.0).rounded() / 1000.0
}

func loadCGImage(_ url: URL) -> CGImage? {
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil) else {
        return nil
    }
    return CGImageSourceCreateImageAtIndex(source, 0, nil)
}

struct RuntimeError: Error, CustomStringConvertible {
    let description: String

    init(_ description: String) {
        self.description = description
    }
}
