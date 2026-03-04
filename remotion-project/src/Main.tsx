import { AbsoluteFill, Audio, Sequence, useVideoConfig, OffthreadVideo, Series, staticFile, Loop } from "remotion";
import { useMemo } from "react";

// 解析 VTT 字幕
function parseVTTContent(vttContent: string): Array<{ start: number; end: number; text: string }> {
  try {
    const lines = vttContent.split("\n");
    const subtitles: Array<{ start: number; end: number; text: string }> = [];
    let i = 0;

    while (i < lines.length && !lines[i].includes("-->")) i++;

    while (i < lines.length) {
      const line = lines[i].trim();
      if (line.includes("-->")) {
        const [startStr, endStr] = line.split("-->").map((s) => s.trim());
        const start = parseTime(startStr);
        const end = parseTime(endStr);

        i++;
        let text = "";
        while (i < lines.length && lines[i].trim() !== "") {
          text += (text ? "\n" : "") + lines[i].trim();
          i++;
        }
        if (text) subtitles.push({ start, end, text });
      }
      i++;
    }
    return subtitles;
  } catch (e) {
    return [];
  }
}

function parseTime(timeStr: string): number {
  const parts = timeStr.split(":");
  if (parts.length === 3) return parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseFloat(parts[2]);
  if (parts.length === 2) return parseInt(parts[0]) * 60 + parseFloat(parts[1]);
  return 0;
}

// 字幕组件
const SubtitleOverlay: React.FC<{ vttContent: string }> = ({ vttContent }) => {
  const { fps } = useVideoConfig();
  const subtitles = useMemo(() => parseVTTContent(vttContent), [vttContent]);

  return (
    <AbsoluteFill style={{ zIndex: 100 }}>
      {subtitles.map((sub, index) => {
        // 关键修复：确保字幕时长绝对不会是 0 帧，至少显示 1 帧，防止崩溃消失
        const startFrame = Math.max(0, Math.floor(sub.start * fps));
        const endFrame = Math.max(startFrame + 1, Math.floor(sub.end * fps));
        const duration = endFrame - startFrame;

        return (
          <Sequence key={index} from={startFrame} durationInFrames={duration}>
            <div style={{ position: "absolute", bottom: "15%", left: "0", width: "100%", display: "flex", justifyContent: "center", alignItems: "center" }}>
              <span style={{ 
                color: "white", fontSize: 60, fontWeight: "bold", fontFamily: "sans-serif", textAlign: "center", maxWidth: "90%",
                textShadow: "0px 4px 10px rgba(0,0,0,0.8)", WebkitTextStroke: "2px black" 
              }}>
                {sub.text}
              </span>
            </div>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

// 单个视频片段组件
const VideoClipItem: React.FC<{ clip: { path: string, originalDuration: number } }> = ({ clip }) => {
  const { fps } = useVideoConfig();
  // 关键修复：使用真实原视频时长换算出帧数，喂给 Loop 组件
  const originalFrames = Math.max(1, Math.round(clip.originalDuration * fps));

  return (
    <AbsoluteFill>
      {/* 关键修复：只有使用 Remotion 官方的 Loop 标签，画面才会在播完后无缝回头 */}
      <Loop durationInFrames={originalFrames}>
        <OffthreadVideo src={staticFile(clip.path)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </Loop>
    </AbsoluteFill>
  );
};

// 主组件
export const Main: React.FC<any> = (props) => {
  if (!props || !props.videoClips || props.videoClips.length === 0) return null;

  const { videoClips, audioPath, vttContent, bgmPath } = props;
  const { durationInFrames } = useVideoConfig();
  const baseClipDurationFrames = Math.floor(durationInFrames / videoClips.length);

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <Series>
        {videoClips.map((clip: any, index: number) => {
          const isLast = index === videoClips.length - 1;
          const clipDuration = isLast ? durationInFrames - (baseClipDurationFrames * (videoClips.length - 1)) : baseClipDurationFrames;

          return (
            <Series.Sequence key={index} durationInFrames={clipDuration}>
              {/* 这里传入了包含真实时长的 clip 对象 */}
              <VideoClipItem clip={clip} />
            </Series.Sequence>
          );
        })}
      </Series>
      
      {/* 背景音乐：音量设置为 0.15（15%），避免盖过人声，并开启循环 */}
      {bgmPath && <Audio src={staticFile(bgmPath)} volume={0.25} loop={true} />}

      {/* 原来的主语音和字幕 */}
      {audioPath && <Audio src={staticFile(audioPath)} />}
      {vttContent && <SubtitleOverlay vttContent={vttContent} />}
    </AbsoluteFill>
  );
};