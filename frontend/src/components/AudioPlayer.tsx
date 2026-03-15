import { useRef, useEffect } from 'react';
import { Download, Trash2 } from 'lucide-react';
import type { AudioFile } from '../types';
import { AudioScriptUtils } from '../types';
import { getAudioFileUrl } from '../services/audioService';

interface AudioPlayerProps {
  audioFiles: AudioFile[];
  onDelete?: (audioFileId: string) => void;
}

export default function AudioPlayer({ audioFiles, onDelete }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const currentAudioFile = audioFiles[0];

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
  }, [audioFiles]);

  const handleDownload = async () => {
    if (!currentAudioFile) return;
    try {
      const url = getAudioFileUrl(currentAudioFile);
      const response = await fetch(url);
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = `script-${currentAudioFile.language_code}.${currentAudioFile.format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error('Failed to download audio:', err);
      alert('Failed to download audio file');
    }
  };

  const handleDelete = () => {
    if (!currentAudioFile || !onDelete) return;
    if (!confirm(`Delete this audio file (${currentAudioFile.language_code})?`)) return;
    onDelete(currentAudioFile.id);
  };

  if (audioFiles.length === 0) {
    return (
      <div className="px-4 py-8 text-center">
        <p className="font-mono text-[10px] tracking-widest uppercase text-faint">No audio files generated yet</p>
        <p className="font-mono text-[10px] text-faint mt-1">Generate audio for this language to get started</p>
      </div>
    );
  }

  if (!currentAudioFile) return null;

  return (
    <div className="bg-parchment border border-border p-4 space-y-3">
      {/* Native audio controls */}
      <audio
        ref={audioRef}
        controls
        src={getAudioFileUrl(currentAudioFile)}
        className="w-full"
      />

      {/* File metadata */}
      <div className="font-mono text-[10px] text-dim flex items-center gap-4">
        <span>Duration: {AudioScriptUtils.formatDuration(currentAudioFile.duration_seconds)}</span>
        <span>Size: {AudioScriptUtils.formatFileSize(currentAudioFile.file_size_bytes)}</span>
        <span className="uppercase">{currentAudioFile.format}</span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-2 border-t border-border">
        <button
          onClick={handleDownload}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border border-gold-dim text-gold font-mono text-[10px] tracking-widest uppercase hover:border-gold hover:bg-gold/5 transition-colors duration-150 cursor-pointer"
        >
          <Download size={12} />
          Download
        </button>
        {onDelete && (
          <button
            onClick={handleDelete}
            className="px-3 py-2 text-rubric-dim hover:text-rubric hover:bg-rubric/10 transition-colors duration-150 cursor-pointer"
            title="Delete audio file"
          >
            <Trash2 size={14} />
          </button>
        )}
      </div>
    </div>
  );
}
