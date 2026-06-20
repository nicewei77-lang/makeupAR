declare module '@azesmway/react-native-unity' {
  import React from 'react';
  import type { StyleProp, ViewStyle } from 'react-native';

  type UnityMessageEvent = {
    nativeEvent: {
      message: string;
    };
  };

  type UnityViewProps = {
    style?: StyleProp<ViewStyle>;
    androidKeepPlayerMounted?: boolean;
    fullScreen?: boolean;
    onUnityMessage?: (event: UnityMessageEvent) => void;
    onPlayerUnload?: (event: UnityMessageEvent) => void;
    onPlayerQuit?: (event: UnityMessageEvent) => void;
  };

  export default class UnityView extends React.Component<UnityViewProps> {
    postMessage(
      gameObject: string,
      methodName: string,
      message: string
    ): void;
    unloadUnity(): void;
    pauseUnity(pause: boolean): void;
    resumeUnity(): void;
  }
}
