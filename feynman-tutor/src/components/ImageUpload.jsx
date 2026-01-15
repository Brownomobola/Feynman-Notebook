import { useState, useRef } from 'react';
import { Upload, X, Image as ImageIcon } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Button from './Button';

const ImageUpload = ({ 
  onImageChange, 
  preview, 
  onClear,
  label = "Upload Image",
  className = "" 
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      onImageChange(file);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      onImageChange(file);
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className={className}>
      <label className="block text-sm font-medium mb-2" style={{ color: 'var(--color-ink)' }}>
        {label}
      </label>
      
      <AnimatePresence mode="wait">
        {preview ? (
          <motion.div
            key="preview"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="relative"
          >
            <div className="relative rounded-lg overflow-hidden border-2 border-gray-200">
              <img 
                src={preview} 
                alt="Preview" 
                className="w-full h-64 object-contain bg-gray-50"
              />
              <button
                onClick={onClear}
                className="absolute top-2 right-2 p-2 bg-white rounded-full shadow-md hover:bg-gray-100 transition-colors"
                style={{ color: 'var(--color-accent)' }}
              >
                <X size={18} />
              </button>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="upload"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={handleClick}
            className={`
              border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
              transition-all duration-200
              ${isDragging 
                ? 'border-accent bg-highlight' 
                : 'border-gray-300 hover:border-accent'
              }
            `}
            style={{
              borderColor: isDragging ? 'var(--color-accent)' : 'var(--color-border)',
              backgroundColor: isDragging ? 'var(--color-highlight)' : 'white'
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
            />
            
            <div className="flex flex-col items-center gap-3">
              <div 
                className="p-4 rounded-full"
                style={{ backgroundColor: 'var(--color-muted)' }}
              >
                {isDragging ? (
                  <ImageIcon size={32} style={{ color: 'var(--color-accent)' }} />
                ) : (
                  <Upload size={32} style={{ color: 'var(--color-ink-light)' }} />
                )}
              </div>
              
              <div>
                <p className="font-medium" style={{ color: 'var(--color-ink)' }}>
                  {isDragging ? 'Drop your image here' : 'Click to upload or drag and drop'}
                </p>
                <p className="text-sm mt-1" style={{ color: 'var(--color-ink-light)' }}>
                  PNG, JPG, or JPEG (max 10MB)
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ImageUpload;
