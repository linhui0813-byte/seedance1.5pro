import { Composition, getInputProps } from "remotion";
import { Main } from "./Main";

// 读取传入的 props
const inputProps = getInputProps();

export const Root = () => {
  const audioDurationInSeconds = (inputProps?.audioDurationInSeconds as number) || 30;

  return (
    <>
      <Composition
        id="Main"
        component={Main}
        durationInFrames={Math.ceil(audioDurationInSeconds * 30)}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
