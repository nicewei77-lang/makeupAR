import AVFoundation
import CoreVideo
import Foundation
import ImageIO

final class MakeupARMediaPipeFrameSource {
  struct Frame {
    let pixelBuffer: CVPixelBuffer
    let timestampMs: Int64
    let orientation: CGImagePropertyOrientation
  }

  func makeFrame(
    pixelBuffer: CVPixelBuffer,
    timestampMs: Int64,
    orientation: CGImagePropertyOrientation
  ) -> Frame {
    Frame(
      pixelBuffer: pixelBuffer,
      timestampMs: timestampMs,
      orientation: orientation
    )
  }
}
