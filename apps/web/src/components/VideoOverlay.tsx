import { useEffect, useMemo, useRef } from "react";

type TrackFrame = {
  frame: number;
  objects: Array<{
    id: string;
    label: string;
    team?: string | null;
    bbox: [number, number, number, number];
    confidence: number;
  }>;
};

type TracksData = {
  meta: { fps: number; frame_count: number; width: number; height: number };
  frames: TrackFrame[];
};

interface VideoOverlayProps {
  src: string;
  tracks: TracksData | null;
  showPlayers: boolean;
  showBall: boolean;
  showTrails: boolean;
  onReady?: (video: HTMLVideoElement | null) => void;
}

const teamColors: Record<string, string> = {
  A: "#4cc9f0",
  B: "#f48c06",
  ball: "#f72585",
};

const VideoOverlay = ({
  src,
  tracks,
  showPlayers,
  showBall,
  showTrails,
  onReady,
}: VideoOverlayProps) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const framesByIndex = useMemo(() => {
    if (!tracks) return [];
    return tracks.frames;
  }, [tracks]);

  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !tracks) return;

    const resizeCanvas = () => {
      canvas.width = video.clientWidth;
      canvas.height = video.clientHeight;
    };

    resizeCanvas();
    const observer = new ResizeObserver(resizeCanvas);
    observer.observe(video);

    const draw = () => {
      const ctx = canvas.getContext("2d");
      if (!ctx || !tracks) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const frameIndex = Math.min(
        Math.floor(video.currentTime * tracks.meta.fps),
        tracks.meta.frame_count - 1
      );
      const frame = framesByIndex[frameIndex];
      if (!frame) return;

      const scaleX = canvas.width / tracks.meta.width;
      const scaleY = canvas.height / tracks.meta.height;

      if (showTrails && showBall) {
        ctx.strokeStyle = "rgba(247, 37, 133, 0.6)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        const start = Math.max(0, frameIndex - 30);
        for (let i = start; i <= frameIndex; i += 1) {
          const trailFrame = framesByIndex[i];
          const ball = trailFrame?.objects.find((obj) => obj.label === "ball");
          if (!ball) continue;
          const [x, y, w, h] = ball.bbox;
          const cx = (x + w / 2) * scaleX;
          const cy = (y + h / 2) * scaleY;
          if (i === start) {
            ctx.moveTo(cx, cy);
          } else {
            ctx.lineTo(cx, cy);
          }
        }
        ctx.stroke();
      }

      frame.objects.forEach((obj) => {
        if (obj.label === "player" && !showPlayers) return;
        if (obj.label === "ball" && !showBall) return;

        const [x, y, w, h] = obj.bbox;
        const color = obj.label === "ball" ? teamColors.ball : teamColors[obj.team ?? "A"];
        ctx.strokeStyle = color;
        ctx.lineWidth = obj.label === "ball" ? 2 : 3;
        ctx.strokeRect(x * scaleX, y * scaleY, w * scaleX, h * scaleY);

        ctx.fillStyle = color;
        ctx.font = "12px 'Space Grotesk', sans-serif";
        ctx.fillText(obj.id, x * scaleX + 4, y * scaleY - 4);
      });
    };

    const onTimeUpdate = () => draw();
    video.addEventListener("timeupdate", onTimeUpdate);
    video.addEventListener("play", onTimeUpdate);
    video.addEventListener("seeked", onTimeUpdate);

    return () => {
      observer.disconnect();
      video.removeEventListener("timeupdate", onTimeUpdate);
      video.removeEventListener("play", onTimeUpdate);
      video.removeEventListener("seeked", onTimeUpdate);
    };
  }, [tracks, framesByIndex, showPlayers, showBall, showTrails]);

  useEffect(() => {
    if (onReady) {
      onReady(videoRef.current);
    }
  }, [onReady]);

  return (
    <div className="video-shell">
      <video ref={videoRef} src={src} controls preload="metadata" />
      <canvas ref={canvasRef} className="overlay" />
    </div>
  );
};

export default VideoOverlay;
