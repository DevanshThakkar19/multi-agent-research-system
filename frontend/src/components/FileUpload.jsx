import React, { useState } from 'react'
import './FileUpload.css'

function FileUpload({ onUploadSuccess }) {
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState(null)
  const [dragActive, setDragActive] = useState(false)

  const handleFileSelect = async (files) => {
    if (!files || files.length === 0) return

    setUploading(true)
    setUploadStatus(null)

    try {
      const file = files[0]
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      })

      const result = await response.json()

      if (result.success) {
        setUploadStatus({ type: 'success', message: `File "${file.name}" uploaded successfully!` })
        if (onUploadSuccess) {
          onUploadSuccess(result.result)
        }
      } else {
        setUploadStatus({ type: 'error', message: result.message || 'Upload failed' })
      }
    } catch (error) {
      setUploadStatus({ type: 'error', message: `Upload failed: ${error.message}` })
    } finally {
      setUploading(false)
    }
  }

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files)
    }
  }

  return (
    <div className="file-upload-container">
      <h3>Upload Documents</h3>
      <p className="upload-description">
        Upload files to your RAG system for document analysis
      </p>

      <div
        className={`file-upload-area ${dragActive ? 'drag-active' : ''} ${uploading ? 'uploading' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-input"
          className="file-input"
          onChange={(e) => handleFileSelect(e.target.files)}
          accept=".pdf,.txt,.docx,.jpg,.jpeg,.png,.mp3,.wav,.mp4,.avi"
          disabled={uploading}
        />
        <label htmlFor="file-input" className="file-label">
          {uploading ? (
            <>
              <div className="spinner"></div>
              <span>Uploading...</span>
            </>
          ) : (
            <>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
              <span className="upload-text">
                <strong>Click to upload</strong> or drag and drop
              </span>
              <span className="upload-hint">
                PDF, TXT, DOCX, Images, Audio, Video
              </span>
            </>
          )}
        </label>
      </div>

      {uploadStatus && (
        <div className={`upload-status ${uploadStatus.type}`}>
          {uploadStatus.type === 'success' ? '✓' : '✗'} {uploadStatus.message}
        </div>
      )}
    </div>
  )
}

export default FileUpload






















