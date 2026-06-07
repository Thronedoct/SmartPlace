export async function buildForegroundPreviewUrl(foregroundFile, maskFile = null) {
  if (!maskFile) return URL.createObjectURL(foregroundFile);

  try {
    const [foregroundImage, maskImage] = await Promise.all([
      loadImageFromFile(foregroundFile),
      loadImageFromFile(maskFile),
    ]);
    const canvas = document.createElement("canvas");
    canvas.width = foregroundImage.naturalWidth || foregroundImage.width;
    canvas.height = foregroundImage.naturalHeight || foregroundImage.height;
    const context = canvas.getContext("2d");
    context.drawImage(foregroundImage, 0, 0, canvas.width, canvas.height);
    const foregroundData = context.getImageData(0, 0, canvas.width, canvas.height);

    const maskCanvas = document.createElement("canvas");
    maskCanvas.width = canvas.width;
    maskCanvas.height = canvas.height;
    const maskContext = maskCanvas.getContext("2d");
    maskContext.drawImage(maskImage, 0, 0, canvas.width, canvas.height);
    const maskData = maskContext.getImageData(0, 0, canvas.width, canvas.height);

    for (let index = 0; index < foregroundData.data.length; index += 4) {
      foregroundData.data[index + 3] = maskData.data[index];
    }
    context.putImageData(foregroundData, 0, 0);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
    if (!blob) return URL.createObjectURL(foregroundFile);
    return URL.createObjectURL(blob);
  } catch (error) {
    return URL.createObjectURL(foregroundFile);
  }
}

function loadImageFromFile(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error(`Could not load ${file.name}`));
    };
    image.src = url;
  });
}
