const ASCII_CHARS = '@%#*+=-:. ';

export function imageToAscii(image, maxWidth = 100, maxHeight = 50) {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  
  let width = image.width;
  let height = image.height;
  
  const ratio = width / height;
  
  if (width > maxWidth) {
    width = maxWidth;
    height = Math.floor(width / ratio / 2);
  }
  
  if (height > maxHeight) {
    height = maxHeight;
    width = Math.floor(height * ratio * 2);
  }
  
  canvas.width = width;
  canvas.height = height;
  
  ctx.drawImage(image, 0, 0, width, height);
  
  const imageData = ctx.getImageData(0, 0, width, height);
  const data = imageData.data;
  
  let ascii = '';
  
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const index = (y * width + x) * 4;
      const r = data[index];
      const g = data[index + 1];
      const b = data[index + 2];
      
      const gray = 0.299 * r + 0.587 * g + 0.114 * b;
      
      const charIndex = Math.floor((gray / 255) * (ASCII_CHARS.length - 1));
      ascii += ASCII_CHARS[charIndex];
    }
    ascii += '\n';
  }
  
  return ascii;
}

export function loadImage(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = e.target.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
