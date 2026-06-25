#!/usr/bin/env swift

import CoreGraphics
import CoreImage
import Foundation
import ImageIO
import Vision

struct GateImageResult {
    let inputPath: String
    let baseName: String
    let width: Int
    let height: Int
    let faceCount: Int
    let outerPointCount: Int
    let innerPointCount: Int
    let status: String
    let hardMaskPath: String
    let featheredMaskPath: String
    let overlayPath: String
    let note: String
}

let arguments = Array(CommandLine.arguments.dropFirst())
var outputDirectory = "evidence/e7-reference-atlas/vision-lip-boundary-v2"
var featherRadius = 5.0
var coordinateMode = "raw-y"
var inputPaths: [String] = []
var index = 0

while index < arguments.count {
    let argument = arguments[index]
    switch argument {
    case "--out":
        index += 1
        guard index < arguments.count else {
            fatalError("--out requires a directory")
        }
        outputDirectory = arguments[index]
    case "--feather":
        index += 1
        guard index < arguments.count, let parsed = Double(arguments[index]) else {
            fatalError("--feather requires a numeric radius")
        }
        featherRadius = parsed
    case "--coordinate-mode":
        index += 1
        guard index < arguments.count else {
            fatalError("--coordinate-mode requires flip-y or raw-y")
        }
        coordinateMode = arguments[index]
        guard coordinateMode == "flip-y" || coordinateMode == "raw-y" else {
            fatalError("--coordinate-mode must be flip-y or raw-y")
        }
    case "--help", "-h":
        print("""
        Usage:
          swift scripts/e7_reference_atlas/run_vision_lip_boundary_gate.swift \\
            --out evidence/e7-reference-atlas/vision-lip-boundary-v2 \\
            --coordinate-mode raw-y \\
            image1.png image2.jpg image3.jpg

        Outputs one hard mask, one feathered mask, one overlay preview per input,
        plus contact_sheet.png, summary.json, and summary.md.
        """)
        exit(0)
    default:
        inputPaths.append(argument)
    }
    index += 1
}

guard !inputPaths.isEmpty else {
    fatalError("Provide at least one input image. The gate decision requires three or more user photos.")
}

let fileManager = FileManager.default
let outputURL = URL(fileURLWithPath: outputDirectory, isDirectory: true)
try fileManager.createDirectory(at: outputURL, withIntermediateDirectories: true)

let ciContext = CIContext(options: [CIContextOption.useSoftwareRenderer: true])
var results: [GateImageResult] = []
var overlayImages: [CGImage] = []

for inputPath in inputPaths {
    do {
        let result = try processImage(
            inputPath: inputPath,
            outputURL: outputURL,
            featherRadius: featherRadius,
            coordinateMode: coordinateMode,
            ciContext: ciContext)
        results.append(result)
        if let overlay = loadCGImage(URL(fileURLWithPath: result.overlayPath)) {
            overlayImages.append(overlay)
        }
        print("vision_lip_boundary status=\(result.status) input=\(inputPath) overlay=\(result.overlayPath)")
    } catch {
        let baseName = sanitizeBaseName(URL(fileURLWithPath: inputPath).deletingPathExtension().lastPathComponent)
        results.append(
            GateImageResult(
                inputPath: inputPath,
                baseName: baseName,
                width: 0,
                height: 0,
                faceCount: 0,
                outerPointCount: 0,
                innerPointCount: 0,
                status: "error",
                hardMaskPath: "",
                featheredMaskPath: "",
                overlayPath: "",
                note: String(describing: error)))
        print("vision_lip_boundary status=error input=\(inputPath) error=\(error)")
    }
}

let contactSheetPath = outputURL.appendingPathComponent("contact_sheet.png")
if !overlayImages.isEmpty, let contactSheet = makeContactSheet(images: overlayImages) {
    try writePNG(contactSheet, to: contactSheetPath)
}

let passedMinimumInputCount = inputPaths.count >= 3
let successfulCount = results.filter { $0.status == "ok" }.count
let summaryStatus: String
if !passedMinimumInputCount {
    summaryStatus = "insufficient_gate_input"
} else if successfulCount == 0 {
    summaryStatus = "vision_request_failed"
} else if successfulCount < inputPaths.count {
    summaryStatus = "partial_outputs_pending_manual_review"
} else {
    summaryStatus = "pending_manual_review"
}

try writeSummaryJson(
    results: results,
    outputURL: outputURL,
    contactSheetPath: contactSheetPath.path,
    featherRadius: featherRadius,
    coordinateMode: coordinateMode,
    passedMinimumInputCount: passedMinimumInputCount,
    summaryStatus: summaryStatus)
try writeSummaryMarkdown(
    results: results,
    outputURL: outputURL,
    contactSheetPath: contactSheetPath.path,
    featherRadius: featherRadius,
    coordinateMode: coordinateMode,
    passedMinimumInputCount: passedMinimumInputCount,
    summaryStatus: summaryStatus)

if !passedMinimumInputCount {
    print("vision_lip_boundary_gate status=insufficient_gate_input requiredImages=3 providedImages=\(inputPaths.count)")
} else {
    print("vision_lip_boundary_gate status=\(summaryStatus) successfulImages=\(successfulCount)/\(inputPaths.count)")
}

func processImage(
    inputPath: String,
    outputURL: URL,
    featherRadius: Double,
    coordinateMode: String,
    ciContext: CIContext) throws -> GateImageResult {
    let inputURL = URL(fileURLWithPath: inputPath)
    guard let cgImage = loadCGImage(inputURL) else {
        throw RuntimeError("could not load image")
    }

    let width = cgImage.width
    let height = cgImage.height
    let request = VNDetectFaceLandmarksRequest()
    if #unavailable(macOS 14.0) {
        request.usesCPUOnly = true
    }
    let handler = VNImageRequestHandler(cgImage: cgImage, orientation: .up, options: [:])
    try handler.perform([request])

    let faces = request.results ?? []
    guard let face = faces.max(by: { faceArea($0) < faceArea($1) }) else {
        throw RuntimeError("no face detected")
    }
    guard let landmarks = face.landmarks,
          let outerLips = landmarks.outerLips,
          let innerLips = landmarks.innerLips else {
        throw RuntimeError("lip landmarks missing")
    }

    let outerPoints = convertLandmarkPoints(
        outerLips,
        width: width,
        height: height,
        coordinateMode: coordinateMode)
    let innerPoints = convertLandmarkPoints(
        innerLips,
        width: width,
        height: height,
        coordinateMode: coordinateMode)
    guard outerPoints.count >= 3, innerPoints.count >= 3 else {
        throw RuntimeError("not enough lip landmark points")
    }

    guard let hardMask = makeLipMask(width: width, height: height, outer: outerPoints, inner: innerPoints) else {
        throw RuntimeError("could not draw lip mask")
    }
    guard let featheredMask = featherMask(hardMask, radius: featherRadius, ciContext: ciContext) else {
        throw RuntimeError("could not feather lip mask")
    }
    guard let overlay = makeOverlay(
        image: cgImage,
        mask: featheredMask,
        outer: outerPoints,
        inner: innerPoints,
        ciContext: ciContext) else {
        throw RuntimeError("could not draw overlay")
    }

    let baseName = sanitizeBaseName(inputURL.deletingPathExtension().lastPathComponent)
    let hardMaskURL = outputURL.appendingPathComponent("\(baseName)_vision_outer_minus_inner_mask.png")
    let featheredMaskURL = outputURL.appendingPathComponent("\(baseName)_vision_feathered_mask.png")
    let overlayURL = outputURL.appendingPathComponent("\(baseName)_vision_overlay.png")
    try writePNG(hardMask, to: hardMaskURL)
    try writePNG(featheredMask, to: featheredMaskURL)
    try writePNG(overlay, to: overlayURL)

    return GateImageResult(
        inputPath: inputPath,
        baseName: baseName,
        width: width,
        height: height,
        faceCount: faces.count,
        outerPointCount: outerPoints.count,
        innerPointCount: innerPoints.count,
        status: "ok",
        hardMaskPath: hardMaskURL.path,
        featheredMaskPath: featheredMaskURL.path,
        overlayPath: overlayURL.path,
        note: "outerLips filled, innerLips excluded, feathered preview generated")
}

func convertLandmarkPoints(
    _ landmark: VNFaceLandmarkRegion2D,
    width: Int,
    height: Int,
    coordinateMode: String) -> [CGPoint] {
    var points: [CGPoint] = []
    points.reserveCapacity(landmark.pointCount)
    let imagePoints = landmark.pointsInImage(imageSize: CGSize(width: width, height: height))
    for point in imagePoints {
        let y = coordinateMode == "raw-y" ? point.y : CGFloat(height) - point.y
        points.append(CGPoint(x: point.x, y: y))
    }
    return points
}

func makeLipMask(width: Int, height: Int, outer: [CGPoint], inner: [CGPoint]) -> CGImage? {
    guard let context = makeGrayContext(width: width, height: height) else {
        return nil
    }
    let rect = CGRect(x: 0, y: 0, width: width, height: height)
    context.setFillColor(gray: 0, alpha: 1)
    context.fill(rect)
    context.setFillColor(gray: 1, alpha: 1)
    context.addPath(closedPath(points: outer))
    context.fillPath()
    context.setFillColor(gray: 0, alpha: 1)
    context.addPath(closedPath(points: inner))
    context.fillPath()
    return context.makeImage()
}

func featherMask(_ mask: CGImage, radius: Double, ciContext: CIContext) -> CGImage? {
    let input = CIImage(cgImage: mask)
    guard let filter = CIFilter(name: "CIGaussianBlur") else {
        return nil
    }
    filter.setValue(input, forKey: kCIInputImageKey)
    filter.setValue(radius, forKey: kCIInputRadiusKey)
    guard let output = filter.outputImage else {
        return nil
    }
    let crop = CGRect(x: 0, y: 0, width: mask.width, height: mask.height)
    return ciContext.createCGImage(output.cropped(to: crop), from: crop)
}

func makeOverlay(
    image: CGImage,
    mask: CGImage,
    outer: [CGPoint],
    inner: [CGPoint],
    ciContext: CIContext) -> CGImage? {
    let width = image.width
    let height = image.height
    let extent = CGRect(x: 0, y: 0, width: width, height: height)
    let background = CIImage(cgImage: image).cropped(to: extent)
    let overlayColor = CIImage(
        color: CIColor(red: 1.0, green: 0.12, blue: 0.38, alpha: 0.38))
        .cropped(to: extent)
    let maskImage = CIImage(cgImage: mask).cropped(to: extent)
    guard let blendFilter = CIFilter(name: "CIBlendWithMask") else {
        return nil
    }
    blendFilter.setValue(overlayColor, forKey: kCIInputImageKey)
    blendFilter.setValue(background, forKey: kCIInputBackgroundImageKey)
    blendFilter.setValue(maskImage, forKey: kCIInputMaskImageKey)
    guard let blendedOutput = blendFilter.outputImage,
          let blendedImage = ciContext.createCGImage(blendedOutput, from: extent) else {
        return nil
    }

    guard let context = makeRGBContext(width: width, height: height) else {
        return nil
    }
    context.draw(blendedImage, in: extent)
    context.setLineJoin(.round)
    context.setLineCap(.round)
    context.setStrokeColor(red: 0.05, green: 1.0, blue: 0.78, alpha: 0.95)
    context.setLineWidth(max(2.0, CGFloat(width) / 360.0))
    context.addPath(closedPath(points: outer))
    context.strokePath()

    context.setStrokeColor(red: 1.0, green: 0.92, blue: 0.18, alpha: 0.95)
    context.addPath(closedPath(points: inner))
    context.strokePath()
    return context.makeImage()
}

func makeContactSheet(images: [CGImage]) -> CGImage? {
    let columns = min(3, max(1, images.count))
    let cellWidth = 360
    let scaledHeights = images.map { image in
        Int((CGFloat(cellWidth) / CGFloat(image.width) * CGFloat(image.height)).rounded(.up))
    }
    let cellHeight = max(1, scaledHeights.max() ?? cellWidth)
    let rows = Int(ceil(Double(images.count) / Double(columns)))
    guard let context = makeRGBContext(width: columns * cellWidth, height: rows * cellHeight) else {
        return nil
    }

    context.setFillColor(red: 0.04, green: 0.04, blue: 0.045, alpha: 1)
    context.fill(CGRect(x: 0, y: 0, width: columns * cellWidth, height: rows * cellHeight))

    for (imageIndex, image) in images.enumerated() {
        let column = imageIndex % columns
        let row = imageIndex / columns
        let scale = CGFloat(cellWidth) / CGFloat(image.width)
        let drawHeight = CGFloat(image.height) * scale
        let x = CGFloat(column * cellWidth)
        let y = CGFloat((rows - 1 - row) * cellHeight)
        let rect = CGRect(x: x, y: y, width: CGFloat(cellWidth), height: drawHeight)
        context.draw(image, in: rect)
    }

    return context.makeImage()
}

func closedPath(points: [CGPoint]) -> CGPath {
    let path = CGMutablePath()
    guard let first = points.first else {
        return path
    }
    path.move(to: first)
    for point in points.dropFirst() {
        path.addLine(to: point)
    }
    path.closeSubpath()
    return path
}

func makeGrayContext(width: Int, height: Int) -> CGContext? {
    let colorSpace = CGColorSpaceCreateDeviceGray()
    return CGContext(
        data: nil,
        width: width,
        height: height,
        bitsPerComponent: 8,
        bytesPerRow: 0,
        space: colorSpace,
        bitmapInfo: CGImageAlphaInfo.none.rawValue)
}

func makeRGBContext(width: Int, height: Int) -> CGContext? {
    let colorSpace = CGColorSpaceCreateDeviceRGB()
    return CGContext(
        data: nil,
        width: width,
        height: height,
        bitsPerComponent: 8,
        bytesPerRow: 0,
        space: colorSpace,
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)
}

func writePNG(_ image: CGImage, to url: URL) throws {
    guard let destination = CGImageDestinationCreateWithURL(
        url as CFURL,
        "public.png" as CFString,
        1,
        nil) else {
        throw RuntimeError("could not create PNG destination: \(url.path)")
    }
    CGImageDestinationAddImage(destination, image, nil)
    if !CGImageDestinationFinalize(destination) {
        throw RuntimeError("could not write PNG: \(url.path)")
    }
}

func loadCGImage(_ url: URL) -> CGImage? {
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil) else {
        return nil
    }
    return CGImageSourceCreateImageAtIndex(source, 0, nil)
}

func writeSummaryJson(
    results: [GateImageResult],
    outputURL: URL,
    contactSheetPath: String,
    featherRadius: Double,
    coordinateMode: String,
    passedMinimumInputCount: Bool,
    summaryStatus: String) throws {
    let resultEntries = results.map { result in
        """
            {
              "inputPath": "\(jsonEscape(result.inputPath))",
              "status": "\(jsonEscape(result.status))",
              "width": \(result.width),
              "height": \(result.height),
              "faceCount": \(result.faceCount),
              "outerPointCount": \(result.outerPointCount),
              "innerPointCount": \(result.innerPointCount),
              "hardMaskPath": "\(jsonEscape(result.hardMaskPath))",
              "featheredMaskPath": "\(jsonEscape(result.featheredMaskPath))",
              "overlayPath": "\(jsonEscape(result.overlayPath))",
              "note": "\(jsonEscape(result.note))"
            }
        """
    }.joined(separator: ",\n")

    let json = """
    {
      "gateId": "vision-lip-boundary-v2",
      "status": "\(summaryStatus)",
      "inputCount": \(results.count),
      "passedMinimumInputCount": \(passedMinimumInputCount),
      "requiredMinimumInputCount": 3,
      "featherRadiusPx": \(String(format: "%.2f", featherRadius)),
      "coordinateMode": "\(jsonEscape(coordinateMode))",
      "contactSheetPath": "\(jsonEscape(contactSheetPath))",
      "baselineMaskSource": "lip-drawn-style-atlas-v1",
      "runtimeIntegrationAllowed": false,
      "runtimeIntegrationCondition": "only if manual review clearly beats lip-drawn-style-atlas-v1",
      "outOfScope": ["Core ML", "MediaPipe runtime", "native Metal", "new camera session", "product readiness"],
      "passCriteria": [
        "mouth corners included",
        "upper lip cupid bow improved",
        "inner mouth and teeth excluded",
        "full lip coverage suitable for matte and gradient"
      ],
      "results": [
    \(resultEntries)
      ]
    }
    """
    try json.write(to: outputURL.appendingPathComponent("summary.json"), atomically: true, encoding: .utf8)
}

func writeSummaryMarkdown(
    results: [GateImageResult],
    outputURL: URL,
    contactSheetPath: String,
    featherRadius: Double,
    coordinateMode: String,
    passedMinimumInputCount: Bool,
    summaryStatus: String) throws {
    var lines: [String] = []
    lines.append("# Vision Lip Boundary Gate v2")
    lines.append("")
    lines.append("- Status: `\(summaryStatus)`")
    lines.append("- Required input count: `3`; provided: `\(results.count)`; minimum passed: `\(passedMinimumInputCount)`")
    lines.append("- Baseline to beat: `lip-drawn-style-atlas-v1`")
    lines.append("- Feather radius: `\(String(format: "%.2f", featherRadius))px`")
    lines.append("- Coordinate mode: `\(coordinateMode)`")
    lines.append("- Contact sheet: `\(contactSheetPath)`")
    lines.append("- Runtime integration allowed now: `false`")
    lines.append("")
    lines.append("Manual review criteria:")
    lines.append("")
    lines.append("- Mouth corners included.")
    lines.append("- Upper lip cupid bow is better than the current atlas.")
    lines.append("- Inner mouth / teeth are excluded.")
    lines.append("- Matte and gradient can keep full lip coverage.")
    lines.append("")
    lines.append("Out of scope: Core ML, MediaPipe runtime, native Metal, new camera session, product readiness.")
    lines.append("")
    lines.append("| Input | Status | Face count | Outer / inner points | Overlay |")
    lines.append("| --- | --- | ---: | ---: | --- |")
    for result in results {
        lines.append("| `\(result.inputPath)` | `\(result.status)` | \(result.faceCount) | \(result.outerPointCount) / \(result.innerPointCount) | `\(result.overlayPath)` |")
    }
    lines.append("")
    try lines.joined(separator: "\n").write(
        to: outputURL.appendingPathComponent("summary.md"),
        atomically: true,
        encoding: .utf8)
}

func faceArea(_ face: VNFaceObservation) -> CGFloat {
    face.boundingBox.width * face.boundingBox.height
}

func sanitizeBaseName(_ value: String) -> String {
    let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "-_"))
    let scalars = value.unicodeScalars.map { scalar -> Character in
        allowed.contains(scalar) ? Character(scalar) : "-"
    }
    let sanitized = String(scalars).trimmingCharacters(in: CharacterSet(charactersIn: "-_"))
    return sanitized.isEmpty ? "image" : sanitized
}

func jsonEscape(_ value: String) -> String {
    value
        .replacingOccurrences(of: "\\", with: "\\\\")
        .replacingOccurrences(of: "\"", with: "\\\"")
        .replacingOccurrences(of: "\n", with: "\\n")
}

struct RuntimeError: Error, CustomStringConvertible {
    let description: String

    init(_ description: String) {
        self.description = description
    }
}
