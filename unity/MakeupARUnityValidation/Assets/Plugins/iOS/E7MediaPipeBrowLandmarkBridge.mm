#include <dlfcn.h>
#include <stdlib.h>
#include <string.h>

typedef const char *(*E7MediaPipeAppDetectFn)(
    const unsigned char *pngBytes,
    int byteCount,
    int imageWidth,
    int imageHeight);
typedef void (*E7MediaPipeAppReleaseFn)(const char *pointer);

static char *E7MediaPipeCopyCString(const char *text)
{
    if (text == NULL)
    {
        text = "";
    }

    size_t length = strlen(text);
    char *copy = (char *)malloc(length + 1);
    if (copy == NULL)
    {
        return NULL;
    }

    memcpy(copy, text, length);
    copy[length] = '\0';
    return copy;
}

static const char *E7MediaPipeMissingAppRuntimeJson(void)
{
    // raw camera frames are memory-only.
    // Diagnostics are landmark, bbox, confidence, timing, and status numbers only.
    return "{\"status\":\"native_runtime_missing\",\"detail\":\"E7MediaPipeAppDetectBrowLandmarksPng_not_found\",\"source\":\"mediapipe_face_landmarker_runtime_brow_landmarks\",\"coordinateMode\":\"image_normalized\",\"faceCount\":0,\"landmarkCount\":0,\"leftPointCount\":0,\"rightPointCount\":0,\"confidence\":0,\"latencyMs\":0,\"rawCameraFrameStored\":false,\"offDeviceUpload\":false}";
}

extern "C" {

const char *E7MediaPipeDetectBrowLandmarksPng(
    const unsigned char *pngBytes,
    int byteCount,
    int imageWidth,
    int imageHeight)
{
    E7MediaPipeAppDetectFn appDetect =
        (E7MediaPipeAppDetectFn)dlsym(RTLD_DEFAULT, "E7MediaPipeAppDetectBrowLandmarksPng");
    if (appDetect == NULL)
    {
        return E7MediaPipeCopyCString(E7MediaPipeMissingAppRuntimeJson());
    }

    return appDetect(pngBytes, byteCount, imageWidth, imageHeight);
}

void E7MediaPipeReleaseCString(const char *pointer)
{
    if (pointer == NULL)
    {
        return;
    }

    E7MediaPipeAppReleaseFn appRelease =
        (E7MediaPipeAppReleaseFn)dlsym(RTLD_DEFAULT, "E7MediaPipeAppReleaseCString");
    if (appRelease != NULL)
    {
        appRelease(pointer);
        return;
    }

    free((void *)pointer);
}

}
