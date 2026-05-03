import { useState, useRef } from 'react'
import { imageToAscii, loadImage } from './utils/imageToAscii'
import './App.css'

function App() {
  const [asciiArt, setAsciiArt] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [fileName, setFileName] = useState('')
  const [width, setWidth] = useState(150)
  const fileInputRef = useRef(null)

  const handleFileChange = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    setIsLoading(true)
    setFileName(file.name)

    try {
      const img = await loadImage(file)
      const ascii = imageToAscii(img, width)
      setAsciiArt(ascii)
    } catch (error) {
      console.error('Error converting image:', error)
      setAsciiArt('转换失败，请重试')
    } finally {
      setIsLoading(false)
    }
  }

  const handleConvert = () => {
    if (fileInputRef.current && fileInputRef.current.files[0]) {
      handleFileChange({ target: fileInputRef.current })
    }
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(asciiArt)
      alert('已复制到剪贴板！')
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  return (
    <div className="container">
      <header className="header">
        <h1>图片转字符画工具</h1>
        <p>上传图片，转换为ASCII字符画</p>
      </header>

      <main className="main">
        <section className="upload-section">
          <div className="upload-controls">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept="image/*"
              className="file-input"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="upload-btn">
              选择图片
            </label>
            {fileName && <span className="file-name">{fileName}</span>}
          </div>

          <div className="settings">
            <label className="width-label">
              字符宽度:
              <input
                type="number"
                value={width}
                onChange={(e) => setWidth(Math.max(50, parseInt(e.target.value) || 150))}
                min="50"
                max="300"
                className="width-input"
              />
            </label>
            {fileName && (
              <button onClick={handleConvert} className="convert-btn" disabled={isLoading}>
                {isLoading ? '转换中...' : '重新转换'}
              </button>
            )}
          </div>
        </section>

        {asciiArt && (
          <section className="result-section">
            <div className="result-header">
              <h2>转换结果</h2>
              <button onClick={handleCopy} className="copy-btn">
                复制到剪贴板
              </button>
            </div>
            <pre className="ascii-output">{asciiArt}</pre>
          </section>
        )}
      </main>

      <footer className="footer">
        <p>基于 React + Vite 构建</p>
      </footer>
    </div>
  )
}

export default App
