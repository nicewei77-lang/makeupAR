#include <dlfcn.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

typedef const char *(*E7MediaPipeAppDetectFullFaceFn)(
    const unsigned char *bgraBytes,
    int byteCount,
    int imageWidth,
    int imageHeight,
    long long timestampMs,
    int orientationDegrees);
typedef const char *(*E7MediaPipeAppDetectFullFaceNativeFrameFn)(
    long long frameHandle,
    long long timestampMs);
typedef void (*E7MediaPipeAppReleaseFn)(const char *pointer);

static char *E7MediaPipeFullFaceCopyCString(const char *text)
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

static const char *E7MediaPipeFullFaceMissingAppRuntimeJson(void)
{
    return "{\"status\":\"native_runtime_missing\",\"detail\":\"E7MediaPipeAppDetectFullFaceBgra_not_found\",\"source\":\"mediapipe_face_landmarker_full_face_v1\",\"inputFormat\":\"bgra-cvpixelbuffer\",\"faceCount\":0,\"landmarkCount\":0,\"faceConfidence\":0,\"latencyMs\":0,\"rawFrameStored\":false,\"offDeviceUpload\":false}";
}

static const char *E7MediaPipeFullFaceNativeFrameNotConnectedJson(long long frameHandle, long long timestampMs)
{
    char buffer[512];
    snprintf(
        buffer,
        sizeof(buffer),
        "{\"status\":\"not_connected\",\"detail\":\"native_frame_handle_not_connected\",\"source\":\"mediapipe_face_landmarker_full_face_v1\",\"inputFormat\":\"native-cvpixelbuffer\",\"frameId\":%lld,\"timestampMs\":%lld,\"imageWidth\":0,\"imageHeight\":0,\"faceCount\":0,\"landmarkCount\":0,\"faceConfidence\":0,\"latencyMs\":0,\"nativeFrameHandle\":%lld,\"available\":false,\"rawFrameStored\":false,\"offDeviceUpload\":false}",
        timestampMs,
        timestampMs,
        frameHandle);
    return E7MediaPipeFullFaceCopyCString(buffer);
}

extern "C" {

const char *E7MediaPipeDetectFullFaceBgra(
    const unsigned char *bgraBytes,
    int byteCount,
    int imageWidth,
    int imageHeight,
    long long timestampMs,
    int orientationDegrees)
{
    E7MediaPipeAppDetectFullFaceFn appDetect =
        (E7MediaPipeAppDetectFullFaceFn)dlsym(RTLD_DEFAULT, "E7MediaPipeAppDetectFullFaceBgra");
    if (appDetect == NULL)
    {
        return E7MediaPipeFullFaceCopyCString(E7MediaPipeFullFaceMissingAppRuntimeJson());
    }

    return appDetect(bgraBytes, byteCount, imageWidth, imageHeight, timestampMs, orientationDegrees);
}

const char *E7MediaPipeDetectFullFaceFromNativeFrame(
    long long frameHandle,
    long long timestampMs)
{
    E7MediaPipeAppDetectFullFaceNativeFrameFn appDetect =
        (E7MediaPipeAppDetectFullFaceNativeFrameFn)dlsym(
            RTLD_DEFAULT,
            "E7MediaPipeAppDetectFullFaceFromNativeFrame");
    if (appDetect == NULL)
    {
        return E7MediaPipeFullFaceNativeFrameNotConnectedJson(frameHandle, timestampMs);
    }

    return appDetect(frameHandle, timestampMs);
}

void E7MediaPipeReleaseFullFaceCString(const char *pointer)
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
