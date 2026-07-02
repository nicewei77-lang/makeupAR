#import <CoreGraphics/CoreGraphics.h>
#import <Foundation/Foundation.h>
#import <ImageIO/ImageIO.h>
#import <UIKit/UIKit.h>
#import <Vision/Vision.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#if __has_include(<MediaPipeTasksVision/MediaPipeTasksVision.h>)
#import <MediaPipeTasksVision/MediaPipeTasksVision.h>
#define E7_HAS_MEDIAPIPE_TASKS 1
#else
#define E7_HAS_MEDIAPIPE_TASKS 0
#endif

#define E7_NATIVE_EXPORT __attribute__((visibility("default")))

static NSString *E7JsonEscape(NSString *value)
{
  if (value == nil) {
    return @"";
  }

  NSMutableString *escaped = [value mutableCopy];
  [escaped replaceOccurrencesOfString:@"\\" withString:@"\\\\" options:0 range:NSMakeRange(0, escaped.length)];
  [escaped replaceOccurrencesOfString:@"\"" withString:@"\\\"" options:0 range:NSMakeRange(0, escaped.length)];
  [escaped replaceOccurrencesOfString:@"\n" withString:@"\\n" options:0 range:NSMakeRange(0, escaped.length)];
  [escaped replaceOccurrencesOfString:@"\r" withString:@"\\r" options:0 range:NSMakeRange(0, escaped.length)];
  return escaped;
}

static char *E7CopyCString(NSString *json)
{
  const char *utf8 = [json UTF8String];
  if (utf8 == NULL) {
    utf8 = "";
  }

  size_t length = strlen(utf8);
  char *copy = (char *)malloc(length + 1);
  if (copy == NULL) {
    return NULL;
  }

  memcpy(copy, utf8, length);
  copy[length] = '\0';
  return copy;
}

static NSString *E7FailureJson(NSString *status, NSString *detail, int imageWidth, int imageHeight)
{
  return [NSString stringWithFormat:
    @"{\"status\":\"%@\",\"detail\":\"%@\",\"source\":\"apple_vision_runtime_lip_landmarks\",\"coordinateMode\":\"raw-y\",\"imageWidth\":%d,\"imageHeight\":%d,\"faceCount\":0,\"outerPointCount\":0,\"innerPointCount\":0,\"outer\":[],\"inner\":[]}",
    E7JsonEscape(status),
    E7JsonEscape(detail),
    imageWidth,
    imageHeight];
}

static NSString *E7EyebrowFailureJson(NSString *status, NSString *detail, int imageWidth, int imageHeight)
{
  return [NSString stringWithFormat:
    @"{\"status\":\"%@\",\"detail\":\"%@\",\"source\":\"mediapipe_face_landmarker_runtime_eyebrow_boundary\",\"coordinateMode\":\"mediapipe-image-top-left\",\"imageWidth\":%d,\"imageHeight\":%d,\"faceCount\":0,\"leftOuterPointCount\":0,\"rightOuterPointCount\":0,\"leftEyePointCount\":0,\"rightEyePointCount\":0,\"leftOuter\":[],\"rightOuter\":[],\"leftEye\":[],\"rightEye\":[]}",
    E7JsonEscape(status),
    E7JsonEscape(detail),
    imageWidth,
    imageHeight];
}

static NSString *E7PointArrayJson(VNFaceLandmarkRegion2D *landmark, CGSize imageSize)
{
  if (landmark == nil || landmark.pointCount == 0) {
    return @"[]";
  }

  const CGPoint *points = [landmark pointsInImageOfSize:imageSize];
  NSMutableArray<NSString *> *items = [NSMutableArray arrayWithCapacity:landmark.pointCount];
  for (NSUInteger index = 0; index < landmark.pointCount; index++) {
    CGPoint point = points[index];
    [items addObject:[NSString stringWithFormat:@"{\"x\":%.3f,\"y\":%.3f}", point.x, point.y]];
  }

  return [NSString stringWithFormat:@"[%@]", [items componentsJoinedByString:@","]];
}

static VNFaceObservation *E7LargestFace(NSArray<VNFaceObservation *> *faces)
{
  VNFaceObservation *largest = nil;
  CGFloat largestArea = 0.0;
  for (VNFaceObservation *face in faces) {
    CGFloat area = face.boundingBox.size.width * face.boundingBox.size.height;
    if (largest == nil || area > largestArea) {
      largest = face;
      largestArea = area;
    }
  }

  return largest;
}

static const int E7MediaPipeBrowGroupA[] = {46, 53, 52, 65, 55, 107, 66, 105, 63, 70};
static const int E7MediaPipeBrowGroupB[] = {276, 283, 282, 295, 285, 336, 296, 334, 293, 300};
static const int E7MediaPipeEyeGroupA[] = {33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246};
static const int E7MediaPipeEyeGroupB[] = {263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466};

#if E7_HAS_MEDIAPIPE_TASKS
static BOOL E7MediaPipeLandmarkPoint(
  NSArray<MPPNormalizedLandmark *> *landmarks,
  int landmarkIndex,
  int imageWidth,
  int imageHeight,
  CGPoint *outPoint)
{
  if (landmarkIndex < 0 || landmarkIndex >= (int)landmarks.count) {
    return NO;
  }

  MPPNormalizedLandmark *landmark = landmarks[(NSUInteger)landmarkIndex];
  if (landmark == nil
      || !isfinite(landmark.x)
      || !isfinite(landmark.y)) {
    return NO;
  }

  if (outPoint != NULL) {
    outPoint->x = landmark.x * imageWidth;
    outPoint->y = landmark.y * imageHeight;
  }
  return YES;
}

static NSString *E7MediaPipePointArrayJson(
  NSArray<MPPNormalizedLandmark *> *landmarks,
  const int *indices,
  NSUInteger indexCount,
  int imageWidth,
  int imageHeight,
  NSUInteger *outPointCount)
{
  if (outPointCount != NULL) {
    *outPointCount = 0;
  }

  if (landmarks == nil || indices == NULL || indexCount == 0) {
    return @"[]";
  }

  NSMutableArray<NSString *> *items = [NSMutableArray arrayWithCapacity:indexCount];
  for (NSUInteger index = 0; index < indexCount; index++) {
    CGPoint point = CGPointZero;
    if (!E7MediaPipeLandmarkPoint(landmarks, indices[index], imageWidth, imageHeight, &point)) {
      continue;
    }

    [items addObject:[NSString stringWithFormat:@"{\"x\":%.3f,\"y\":%.3f}", point.x, point.y]];
  }

  if (outPointCount != NULL) {
    *outPointCount = items.count;
  }

  return [NSString stringWithFormat:@"[%@]", [items componentsJoinedByString:@","]];
}

static CGFloat E7MediaPipeMeanX(
  NSArray<MPPNormalizedLandmark *> *landmarks,
  const int *indices,
  NSUInteger indexCount,
  int imageWidth,
  int imageHeight)
{
  CGFloat totalX = 0.0;
  NSUInteger validCount = 0;
  for (NSUInteger index = 0; index < indexCount; index++) {
    CGPoint point = CGPointZero;
    if (!E7MediaPipeLandmarkPoint(landmarks, indices[index], imageWidth, imageHeight, &point)) {
      continue;
    }

    totalX += point.x;
    validCount++;
  }

  return validCount > 0 ? totalX / validCount : CGFLOAT_MAX;
}

static NSString *E7MediaPipeEyebrowStripJson(
  NSArray<MPPNormalizedLandmark *> *landmarks,
  const int *browIndices,
  NSUInteger browIndexCount,
  const int *eyeIndices,
  NSUInteger eyeIndexCount,
  int imageWidth,
  int imageHeight,
  NSUInteger *outPointCount)
{
  if (outPointCount != NULL) {
    *outPointCount = 0;
  }

  if (landmarks == nil || browIndices == NULL || browIndexCount < 2) {
    return @"[]";
  }

  NSMutableArray<NSValue *> *browPoints = [NSMutableArray arrayWithCapacity:browIndexCount];
  CGFloat browMeanY = 0.0;
  CGFloat minX = CGFLOAT_MAX;
  CGFloat maxX = -CGFLOAT_MAX;

  for (NSUInteger index = 0; index < browIndexCount; index++) {
    CGPoint point = CGPointZero;
    if (!E7MediaPipeLandmarkPoint(landmarks, browIndices[index], imageWidth, imageHeight, &point)) {
      continue;
    }

    [browPoints addObject:[NSValue valueWithCGPoint:point]];
    browMeanY += point.y;
    minX = MIN(minX, point.x);
    maxX = MAX(maxX, point.x);
  }

  if (browPoints.count < 2) {
    return @"[]";
  }

  browMeanY /= browPoints.count;
  NSArray<NSValue *> *sortedBrowPoints = [browPoints sortedArrayUsingComparator:^NSComparisonResult(NSValue *lhs, NSValue *rhs) {
    CGFloat leftX = lhs.CGPointValue.x;
    CGFloat rightX = rhs.CGPointValue.x;
    if (leftX < rightX) {
      return NSOrderedAscending;
    }
    if (leftX > rightX) {
      return NSOrderedDescending;
    }
    return NSOrderedSame;
  }];

  CGFloat eyeMeanY = 0.0;
  NSUInteger eyeValidCount = 0;
  for (NSUInteger index = 0; index < eyeIndexCount; index++) {
    CGPoint point = CGPointZero;
    if (!E7MediaPipeLandmarkPoint(landmarks, eyeIndices[index], imageWidth, imageHeight, &point)) {
      continue;
    }

    eyeMeanY += point.y;
    eyeValidCount++;
  }
  eyeMeanY = eyeValidCount > 0 ? eyeMeanY / eyeValidCount : browMeanY + 1.0;

  CGFloat browWidth = MAX(8.0, maxX - minX);
  CGFloat directionAwayFromEye = browMeanY <= eyeMeanY ? -1.0 : 1.0;
  CGFloat upperOffset = MAX(3.5, MIN(16.0, browWidth * 0.066));
  CGFloat lowerOffset = MAX(2.5, MIN(10.0, browWidth * 0.042));
  CGFloat endpointExtend = MAX(3.0, MIN(14.0, browWidth * 0.046));
  NSUInteger pointCount = sortedBrowPoints.count;
  NSMutableArray<NSString *> *items = [NSMutableArray arrayWithCapacity:pointCount * 2];

  for (NSUInteger index = 0; index < pointCount; index++) {
    CGPoint point = sortedBrowPoints[index].CGPointValue;
    if (index == 0 || index + 1 == pointCount) {
      NSUInteger neighborIndex = index == 0 ? 1 : pointCount - 2;
      CGPoint neighbor = sortedBrowPoints[neighborIndex].CGPointValue;
      CGFloat length = MAX(1.0, hypot(point.x - neighbor.x, point.y - neighbor.y));
      point.x += (point.x - neighbor.x) / length * endpointExtend;
      point.y += (point.y - neighbor.y) / length * endpointExtend * 0.22;
    }

    CGFloat taper = (index == 0 || index + 1 == pointCount)
      ? 0.18
      : (index == 1 || index + 2 == pointCount)
      ? 0.54
      : 1.0;
    CGFloat y = point.y + directionAwayFromEye * upperOffset * taper;
    [items addObject:[NSString stringWithFormat:@"{\"x\":%.3f,\"y\":%.3f}", point.x, y]];
  }

  for (NSInteger index = (NSInteger)pointCount - 1; index >= 0; index--) {
    CGPoint point = sortedBrowPoints[(NSUInteger)index].CGPointValue;
    if (index == 0 || (NSUInteger)index + 1 == pointCount) {
      NSUInteger neighborIndex = index == 0 ? 1 : pointCount - 2;
      CGPoint neighbor = sortedBrowPoints[neighborIndex].CGPointValue;
      CGFloat length = MAX(1.0, hypot(point.x - neighbor.x, point.y - neighbor.y));
      point.x += (point.x - neighbor.x) / length * endpointExtend;
      point.y += (point.y - neighbor.y) / length * endpointExtend * 0.22;
    }

    CGFloat taper = (index == 0 || (NSUInteger)index + 1 == pointCount)
      ? 0.14
      : (index == 1 || (NSUInteger)index + 2 == pointCount)
      ? 0.48
      : 1.0;
    CGFloat y = point.y - directionAwayFromEye * lowerOffset * taper;
    [items addObject:[NSString stringWithFormat:@"{\"x\":%.3f,\"y\":%.3f}", point.x, y]];
  }

  if (outPointCount != NULL) {
    *outPointCount = items.count;
  }

  return [NSString stringWithFormat:@"[%@]", [items componentsJoinedByString:@","]];
}

static NSString *E7MediaPipeFaceLandmarkerModelPath(void)
{
  NSArray<NSBundle *> *bundles = [[NSBundle allBundles] arrayByAddingObjectsFromArray:[NSBundle allFrameworks]];
  for (NSBundle *bundle in bundles) {
    NSString *path = [bundle pathForResource:@"face_landmarker" ofType:@"task"];
    if (path.length > 0) {
      return path;
    }

    path = [bundle pathForResource:@"face_landmarker" ofType:@"task" inDirectory:@"E7Models"];
    if (path.length > 0) {
      return path;
    }

    path = [bundle pathForResource:@"face_landmarker" ofType:@"task" inDirectory:@"Data/Raw"];
    if (path.length > 0) {
      return path;
    }
  }

  return nil;
}

static MPPFaceLandmarker *E7SharedMediaPipeFaceLandmarker(NSString *modelPath, NSError **error)
{
  static MPPFaceLandmarker *cachedLandmarker = nil;
  static NSString *cachedModelPath = nil;

  if (modelPath.length == 0) {
    return nil;
  }

  @synchronized([MPPFaceLandmarker class]) {
    if (cachedLandmarker != nil && [cachedModelPath isEqualToString:modelPath]) {
      return cachedLandmarker;
    }

    MPPFaceLandmarkerOptions *options = [[MPPFaceLandmarkerOptions alloc] init];
    options.baseOptions.modelAssetPath = modelPath;
    options.runningMode = MPPRunningModeImage;
    options.numFaces = 1;
    options.minFaceDetectionConfidence = 0.35f;
    options.minFacePresenceConfidence = 0.35f;
    options.minTrackingConfidence = 0.35f;
    options.outputFaceBlendshapes = NO;
    options.outputFacialTransformationMatrixes = NO;

    MPPFaceLandmarker *landmarker = [[MPPFaceLandmarker alloc] initWithOptions:options error:error];
    if (landmarker == nil || (error != NULL && *error != nil)) {
      return nil;
    }

    cachedLandmarker = landmarker;
    cachedModelPath = [modelPath copy];
    return cachedLandmarker;
  }
}
#endif

extern "C" {

E7_NATIVE_EXPORT const char *E7VisionDetectLipBoundaryPng(
  const unsigned char *pngBytes,
  int byteCount,
  int imageWidth,
  int imageHeight)
{
  @autoreleasepool {
    if (pngBytes == NULL || byteCount <= 0) {
      return E7CopyCString(E7FailureJson(@"invalid_input", @"png_bytes_empty", imageWidth, imageHeight));
    }

    NSData *data = [NSData dataWithBytes:pngBytes length:(NSUInteger)byteCount];
    CGImageSourceRef imageSource = CGImageSourceCreateWithData((__bridge CFDataRef)data, NULL);
    if (imageSource == NULL) {
      return E7CopyCString(E7FailureJson(@"decode_failed", @"cg_image_source_null", imageWidth, imageHeight));
    }

    CGImageRef image = CGImageSourceCreateImageAtIndex(imageSource, 0, NULL);
    CFRelease(imageSource);
    if (image == NULL) {
      return E7CopyCString(E7FailureJson(@"decode_failed", @"cg_image_null", imageWidth, imageHeight));
    }

    int width = (int)CGImageGetWidth(image);
    int height = (int)CGImageGetHeight(image);
    VNDetectFaceLandmarksRequest *request = [[VNDetectFaceLandmarksRequest alloc] init];
    VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithCGImage:image
                                                                        orientation:kCGImagePropertyOrientationUp
                                                                            options:@{}];
    NSError *error = nil;
    BOOL performed = [handler performRequests:@[request] error:&error];
    CGImageRelease(image);

    if (!performed || error != nil) {
      NSString *detail = error != nil ? error.localizedDescription : @"perform_request_failed";
      return E7CopyCString(E7FailureJson(@"vision_request_failed", detail, width, height));
    }

    NSArray<VNFaceObservation *> *faces = request.results;
    VNFaceObservation *face = E7LargestFace(faces);
    if (face == nil) {
      return E7CopyCString(E7FailureJson(@"no_face", @"no_face_observation", width, height));
    }

    VNFaceLandmarks2D *landmarks = face.landmarks;
    VNFaceLandmarkRegion2D *outerLips = landmarks.outerLips;
    VNFaceLandmarkRegion2D *innerLips = landmarks.innerLips;
    if (outerLips == nil || innerLips == nil || outerLips.pointCount < 3 || innerLips.pointCount < 3) {
      return E7CopyCString(E7FailureJson(@"lip_landmarks_missing", @"outer_or_inner_lips_missing", width, height));
    }

    CGSize imageSize = CGSizeMake(width, height);
    NSString *outerJson = E7PointArrayJson(outerLips, imageSize);
    NSString *innerJson = E7PointArrayJson(innerLips, imageSize);
    NSString *json = [NSString stringWithFormat:
      @"{\"status\":\"ok\",\"detail\":\"outerLips_innerLips\",\"source\":\"apple_vision_runtime_lip_landmarks\",\"coordinateMode\":\"raw-y\",\"imageWidth\":%d,\"imageHeight\":%d,\"faceCount\":%lu,\"outerPointCount\":%lu,\"innerPointCount\":%lu,\"outer\":%@,\"inner\":%@}",
      width,
      height,
      (unsigned long)faces.count,
      (unsigned long)outerLips.pointCount,
      (unsigned long)innerLips.pointCount,
      outerJson,
      innerJson];
    return E7CopyCString(json);
  }
}

E7_NATIVE_EXPORT const char *E7MediaPipeDetectEyebrowBoundaryPng(
  const unsigned char *pngBytes,
  int byteCount,
  int imageWidth,
  int imageHeight)
{
  @autoreleasepool {
#if !E7_HAS_MEDIAPIPE_TASKS
    return E7CopyCString(E7EyebrowFailureJson(
      @"mediapipe_tasks_vision_unavailable",
      @"MediaPipeTasksVision framework is not linked into the Unity iOS target",
      imageWidth,
      imageHeight));
#else
    if (pngBytes == NULL || byteCount <= 0) {
      return E7CopyCString(E7EyebrowFailureJson(@"invalid_input", @"png_bytes_empty", imageWidth, imageHeight));
    }

    NSData *data = [NSData dataWithBytes:pngBytes length:(NSUInteger)byteCount];
    CGImageSourceRef imageSource = CGImageSourceCreateWithData((__bridge CFDataRef)data, NULL);
    if (imageSource == NULL) {
      return E7CopyCString(E7EyebrowFailureJson(@"decode_failed", @"cg_image_source_null", imageWidth, imageHeight));
    }

    CGImageRef image = CGImageSourceCreateImageAtIndex(imageSource, 0, NULL);
    CFRelease(imageSource);
    if (image == NULL) {
      return E7CopyCString(E7EyebrowFailureJson(@"decode_failed", @"cg_image_null", imageWidth, imageHeight));
    }

    int width = (int)CGImageGetWidth(image);
    int height = (int)CGImageGetHeight(image);
    UIImage *uiImage = [[UIImage alloc] initWithCGImage:image scale:1.0 orientation:UIImageOrientationUp];
    CGImageRelease(image);
    if (uiImage == nil) {
      return E7CopyCString(E7EyebrowFailureJson(@"decode_failed", @"ui_image_null", width, height));
    }

    NSString *modelPath = E7MediaPipeFaceLandmarkerModelPath();
    if (modelPath.length == 0) {
      return E7CopyCString(E7EyebrowFailureJson(@"mediapipe_model_missing", @"face_landmarker.task_not_found_in_bundle", width, height));
    }

    NSError *error = nil;
    MPPFaceLandmarker *landmarker = E7SharedMediaPipeFaceLandmarker(modelPath, &error);
    if (landmarker == nil || error != nil) {
      NSString *detail = error != nil ? error.localizedDescription : @"face_landmarker_init_failed";
      return E7CopyCString(E7EyebrowFailureJson(@"mediapipe_init_failed", detail, width, height));
    }

    MPPImage *mediaPipeImage = [[MPPImage alloc] initWithUIImage:uiImage orientation:UIImageOrientationUp error:&error];
    if (mediaPipeImage == nil || error != nil) {
      NSString *detail = error != nil ? error.localizedDescription : @"mp_image_init_failed";
      return E7CopyCString(E7EyebrowFailureJson(@"mediapipe_image_failed", detail, width, height));
    }

    MPPFaceLandmarkerResult *result = [landmarker detectImage:mediaPipeImage error:&error];
    if (result == nil || error != nil) {
      NSString *detail = error != nil ? error.localizedDescription : @"detect_image_failed";
      return E7CopyCString(E7EyebrowFailureJson(@"mediapipe_detect_failed", detail, width, height));
    }

    NSArray<NSArray<MPPNormalizedLandmark *> *> *faces = result.faceLandmarks;
    if (faces.count == 0 || faces.firstObject.count < 467) {
      return E7CopyCString(E7EyebrowFailureJson(@"no_face", @"mediapipe_face_landmarks_missing", width, height));
    }

    NSArray<MPPNormalizedLandmark *> *landmarks = faces.firstObject;
    NSUInteger browACount = 0;
    NSUInteger browBCount = 0;
    NSUInteger eyeACount = 0;
    NSUInteger eyeBCount = 0;
    NSString *browAJson = E7MediaPipeEyebrowStripJson(
      landmarks,
      E7MediaPipeBrowGroupA,
      sizeof(E7MediaPipeBrowGroupA) / sizeof(E7MediaPipeBrowGroupA[0]),
      E7MediaPipeEyeGroupA,
      sizeof(E7MediaPipeEyeGroupA) / sizeof(E7MediaPipeEyeGroupA[0]),
      width,
      height,
      &browACount);
    NSString *browBJson = E7MediaPipeEyebrowStripJson(
      landmarks,
      E7MediaPipeBrowGroupB,
      sizeof(E7MediaPipeBrowGroupB) / sizeof(E7MediaPipeBrowGroupB[0]),
      E7MediaPipeEyeGroupB,
      sizeof(E7MediaPipeEyeGroupB) / sizeof(E7MediaPipeEyeGroupB[0]),
      width,
      height,
      &browBCount);
    NSString *eyeAJson = E7MediaPipePointArrayJson(
      landmarks,
      E7MediaPipeEyeGroupA,
      sizeof(E7MediaPipeEyeGroupA) / sizeof(E7MediaPipeEyeGroupA[0]),
      width,
      height,
      &eyeACount);
    NSString *eyeBJson = E7MediaPipePointArrayJson(
      landmarks,
      E7MediaPipeEyeGroupB,
      sizeof(E7MediaPipeEyeGroupB) / sizeof(E7MediaPipeEyeGroupB[0]),
      width,
      height,
      &eyeBCount);

    if (browACount < 3 || browBCount < 3 || eyeACount < 3 || eyeBCount < 3) {
      return E7CopyCString(E7EyebrowFailureJson(@"eyebrow_landmarks_missing", @"mediapipe_brow_or_eye_points_too_sparse", width, height));
    }

    CGFloat browAMeanX = E7MediaPipeMeanX(
      landmarks,
      E7MediaPipeBrowGroupA,
      sizeof(E7MediaPipeBrowGroupA) / sizeof(E7MediaPipeBrowGroupA[0]),
      width,
      height);
    CGFloat browBMeanX = E7MediaPipeMeanX(
      landmarks,
      E7MediaPipeBrowGroupB,
      sizeof(E7MediaPipeBrowGroupB) / sizeof(E7MediaPipeBrowGroupB[0]),
      width,
      height);
    BOOL groupAIsScreenLeft = browAMeanX <= browBMeanX;
    NSString *leftOuterJson = groupAIsScreenLeft ? browAJson : browBJson;
    NSString *rightOuterJson = groupAIsScreenLeft ? browBJson : browAJson;
    NSString *leftEyeJson = groupAIsScreenLeft ? eyeAJson : eyeBJson;
    NSString *rightEyeJson = groupAIsScreenLeft ? eyeBJson : eyeAJson;
    NSUInteger leftOuterCount = groupAIsScreenLeft ? browACount : browBCount;
    NSUInteger rightOuterCount = groupAIsScreenLeft ? browBCount : browACount;
    NSUInteger leftEyeCount = groupAIsScreenLeft ? eyeACount : eyeBCount;
    NSUInteger rightEyeCount = groupAIsScreenLeft ? eyeBCount : eyeACount;

    NSString *json = [NSString stringWithFormat:
      @"{\"status\":\"ok\",\"detail\":\"mediapipe_brow_landmarks_eye_exclusion_screen_sorted\",\"source\":\"mediapipe_face_landmarker_runtime_eyebrow_boundary\",\"coordinateMode\":\"mediapipe-image-top-left\",\"imageWidth\":%d,\"imageHeight\":%d,\"faceCount\":%lu,\"leftOuterPointCount\":%lu,\"rightOuterPointCount\":%lu,\"leftEyePointCount\":%lu,\"rightEyePointCount\":%lu,\"leftOuter\":%@,\"rightOuter\":%@,\"leftEye\":%@,\"rightEye\":%@}",
      width,
      height,
      (unsigned long)faces.count,
      (unsigned long)leftOuterCount,
      (unsigned long)rightOuterCount,
      (unsigned long)leftEyeCount,
      (unsigned long)rightEyeCount,
      leftOuterJson,
      rightOuterJson,
      leftEyeJson,
      rightEyeJson];
    return E7CopyCString(json);
#endif
  }
}

E7_NATIVE_EXPORT void E7VisionReleaseCString(const char *pointer)
{
  if (pointer != NULL) {
    free((void *)pointer);
  }
}

}
