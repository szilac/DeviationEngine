import { useState, useEffect } from 'react';
import type { TimelineImage, Timeline } from '../types';
import { ImageUtils } from '../types';
import { getTimelineImages, deleteTimelineImage } from '../services/api';
import { Image, Download, X, Trash2 } from 'lucide-react';

interface ImageGalleryProps {
  timeline: Timeline;
  generationId?: string;
  onImageDeleted?: () => void;
}

const ImageGallery = ({ timeline, generationId, onImageDeleted }: ImageGalleryProps) => {
  const [images, setImages] = useState<TimelineImage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<TimelineImage | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => { loadImages(); }, [timeline.id, generationId]);

  const loadImages = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await getTimelineImages(timeline.id, generationId);
      if (response.error) setError(response.error.message);
      else if (response.data) setImages(ImageUtils.sortImagesByOrder(response.data));
    } catch {
      setError('Failed to load images');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (imageId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this image? This cannot be undone.')) return;
    setDeletingId(imageId);
    try {
      const response = await deleteTimelineImage(imageId);
      if (response.error) setError(`Failed to delete: ${response.error.message}`);
      else {
        setImages((prev) => prev.filter((img) => img.id !== imageId));
        onImageDeleted?.();
      }
    } catch {
      setError('Failed to delete image');
    } finally {
      setDeletingId(null);
    }
  };

  const handleDownload = async (image: TimelineImage) => {
    try {
      const response = await fetch(image.image_url, { mode: 'cors' });
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${image.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch {
      window.open(image.image_url, '_blank');
    }
  };

  const getAbsoluteYear = (eventYear: number | null): string => {
    if (eventYear === null) return '??';
    return String(new Date(timeline.root_deviation_date).getFullYear() + eventYear);
  };

  // ── Loading ──
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="font-mono text-xs text-dim tracking-widest uppercase animate-pulse">
          Loading images…
        </p>
      </div>
    );
  }

  // ── Error ──
  if (error) {
    return (
      <div className="py-8">
        <div className="border border-rubric-dim px-4 py-3 mb-4">
          <p className="font-mono text-xs text-rubric">{error}</p>
        </div>
        <button
          onClick={loadImages}
          className="font-mono text-[10px] tracking-widest uppercase text-dim hover:text-ink transition-colors cursor-pointer"
        >
          Retry
        </button>
      </div>
    );
  }

  // ── Empty ──
  if (images.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <Image size={32} className="text-faint mb-4" />
        <p className="font-display text-xl text-dim mb-2">No Images Yet</p>
        <p className="font-body text-sm text-faint max-w-sm">
          Use the "+ Generate Images" button to create period-appropriate AI imagery for this chronicle.
        </p>
      </div>
    );
  }

  // ── Gallery ──
  return (
    <div id="image-gallery" className="scroll-mt-24">
      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {images.map((image) => (
          <div
            key={image.id}
            onClick={() => setSelectedImage(image)}
            className="group relative bg-surface border border-border hover:border-gold-dim transition-colors duration-150 cursor-pointer corner-brackets"
          >
            <div className="p-5 min-h-[180px] flex flex-col justify-between">
              <div>
                {/* Year badge */}
                {image.event_year !== null && (
                  <p className="font-mono text-[10px] text-rubric tracking-widest mb-2">
                    {getAbsoluteYear(image.event_year)}
                  </p>
                )}

                {/* Title */}
                <h3 className="font-display text-base text-ink leading-snug line-clamp-2 mb-2">
                  {image.title}
                </h3>

                {/* Description */}
                {image.description && (
                  <p className="font-body text-sm text-dim line-clamp-3">{image.description}</p>
                )}
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between mt-4 pt-3 border-t border-border">
                <span className="font-mono text-[10px] text-faint tracking-widest uppercase">
                  View image →
                </span>
                <button
                  onClick={(e) => handleDelete(image.id, e)}
                  disabled={deletingId === image.id}
                  className="text-faint hover:text-rubric transition-colors opacity-0 group-hover:opacity-100 disabled:opacity-50 cursor-pointer"
                  title="Delete image"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Lightbox */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-50 bg-vellum/95 flex items-start justify-center p-6 overflow-y-auto"
          onClick={() => setSelectedImage(null)}
        >
          <div
            className="relative max-w-4xl w-full my-8"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Lightbox header */}
            <div className="flex items-center justify-between mb-4 border-b border-border pb-3">
              <div>
                <p className="rubric-label mb-1">§ Image</p>
                <h2 className="font-display text-xl text-gold">{selectedImage.title}</h2>
                {selectedImage.event_year !== null && (
                  <p className="font-mono text-[10px] text-dim mt-0.5">
                    Year {getAbsoluteYear(selectedImage.event_year)}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleDownload(selectedImage)}
                  className="font-mono text-[10px] tracking-widest uppercase text-dim hover:text-gold transition-colors flex items-center gap-1.5 cursor-pointer"
                >
                  <Download size={11} /> Download
                </button>
                <button
                  onClick={() => setSelectedImage(null)}
                  className="font-mono text-[10px] tracking-widest uppercase text-dim hover:text-ink transition-colors flex items-center gap-1.5 ml-2 cursor-pointer"
                >
                  <X size={11} /> Close
                </button>
              </div>
            </div>

            {/* Full image */}
            <div className="flex justify-center mb-6">
              <img
                src={selectedImage.image_url}
                alt={selectedImage.title}
                className="max-w-full max-h-[60vh] object-contain"
                crossOrigin="anonymous"
              />
            </div>

            {/* Details */}
            <div className="border border-border p-5 corner-brackets">
              {selectedImage.description && (
                <p className="font-body text-base text-ink mb-4">{selectedImage.description}</p>
              )}

              <div className="grid grid-cols-2 gap-4 text-[10px] font-mono text-dim border-t border-border pt-4 mt-4">
                {selectedImage.model_provider && (
                  <div>
                    <span className="text-faint tracking-widest uppercase block mb-1">Prompt model</span>
                    <span className="text-ink">{selectedImage.model_provider} · {selectedImage.model_name}</span>
                  </div>
                )}
                <div>
                  <span className="text-faint tracking-widest uppercase block mb-1">Generated</span>
                  <span className="text-ink">
                    {new Date(selectedImage.generated_at).toLocaleDateString('en-US', {
                      year: 'numeric', month: 'long', day: 'numeric',
                    })}
                  </span>
                </div>
                {selectedImage.is_user_modified && (
                  <div className="col-span-2">
                    <span className="border border-gold-dim text-gold text-[10px] px-2 py-0.5 tracking-widest uppercase">
                      User Modified
                    </span>
                  </div>
                )}
              </div>

              <details className="mt-4 border-t border-border pt-4">
                <summary className="font-mono text-[10px] tracking-widest uppercase text-dim hover:text-ink cursor-pointer">
                  § Image Prompt
                </summary>
                <p className="mt-3 font-mono text-[11px] text-faint whitespace-pre-wrap leading-relaxed">
                  {selectedImage.prompt_text}
                </p>
              </details>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ImageGallery;
