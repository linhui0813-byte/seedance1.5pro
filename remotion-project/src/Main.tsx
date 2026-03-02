import { AbsoluteFill, Audio, Sequence, useVideoConfig, OffthreadVideo, Series, staticFile } from "remotion";
import { useMemo } from "react";

// 解析 VTT 字幕内容字符串
function parseVTTContent(vttContent: string): Array<{ start: number; end: number; text: string }> {
  try {
    const lines = vttContent.split("\n");
    const subtitles: Array<{ start: number; end: number; text: string }> = [];
    let i = 0;

    // 跳过 WEBVTT 和空行
    while (i < lines.length && !lines[i].includes("-->")) {
      i++;
    }

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

        if (text) {
          subtitles.push({ start, end, text });
        }
      }
      i++;
    }

    return subtitles;
  } catch (e) {
    console.error("Error parsing VTT:", e);
    return [];
  }
}

function parseTime(timeStr: string): number {
  // 格式: HH:MM:SS.mmm 或 MM:SS.mmm
  const parts = timeStr.split(":");
  let seconds = 0;

  if (parts.length === 3) {
    seconds = parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseFloat(parts[2]);
  } else if (parts.length === 2) {
    seconds = parseInt(parts[0]) * 60 + parseFloat(parts[1]);
  }

  return seconds;
}

// 字幕组件 - 直接接收 VTT 内容字符串
const SubtitleOverlay: React.FC<{ vttContent: string }> = ({ vttContent }) => {
  const { fps } = useVideoConfig();
  const subtitles = useMemo(() => parseVTTContent(vttContent), [vttContent]);

  return (
    <div
      style={{
        position: "absolute",
        bottom: "10%",
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {subtitles.map((sub, index) => (
        <Sequence
          key={index}
          from={Math.floor(sub.start * fps)}
          durationInFrames={Math.floor((sub.end - sub.start) * fps)}
        >
          <div
            style={{
              maxWidth: "80%",
              textAlign: "center",
            }}
          >
            <span
              style={{
                color: "white",
                fontSize: 48,
                fontWeight: "bold",
                fontFamily: "PingFang SC, Microsoft YaHei, sans-serif",
                lineHeight: 1.4,
                // 去除背景，添加描边和阴影增强清晰度
                textShadow: "0px 4px 10px rgba(0, 0, 0, 0.8), 0px 0px 4px rgba(0, 0, 0, 0.8)",
                WebkitTextStroke: "1.5px black",
              }}
            >
              {sub.text}
            </span>
          </div>
        </Sequence>
      ))}
    </div>
  );
};

// 单个视频片段组件 - 使用 staticFile
const VideoClipItem: React.FC<{ src: string; duration: number }> = ({ src, duration }) => {
  return (
    <AbsoluteFill>
      <OffthreadVideo
        src={staticFile(src)}
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />
    </AbsoluteFill>
  );
};

// 主组件 - 使用 any 类型
export const Main: React.FC<any> = (props) => {
  // 防御性检查：防止 props 未加载或数据为空导致白屏
  if (!props || !props.videoClips || props.videoClips.length === 0) {
    return (
      <AbsoluteFill style={{ backgroundColor: "#000", justifyContent: "center", alignItems: "center" }}>
        <span style={{ color: "white", fontSize: 24 }}>正在加载视频素材...</span>
      </AbsoluteFill>
    );
  }

  const { audioDurationInSeconds, videoClips, audioPath, vttContent } = props;
  const { fps, durationInFrames } = useVideoConfig();

  // 计算每个视频片段的时长
  const clipDurationFrames = Math.floor(durationInFrames / videoClips.length);

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* 使用 Series 串联视频片段 */}
      <Series>
        {videoClips.map((clip: string, index: number) => (
          <Series.Sequence
            key={index}
            durationInFrames={clipDurationFrames}
          >
            <VideoClipItem src={clip} duration={clipDurationFrames} />
          </Series.Sequence>
        ))}
      </Series>

      {/* 字幕 - 接收 VTT 内容字符串 */}
      {vttContent && <SubtitleOverlay vttContent={vttContent} />}

      {/* 音频 - 使用 staticFile */}
      {audioPath && <Audio src={staticFile(audioPath)} />}
    </AbsoluteFill>
  );
};
