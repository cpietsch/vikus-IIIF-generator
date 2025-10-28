import express from 'express';
import sharpsheet from 'sharpsheet/src/sharpsheet.js';

const app = express();
const PORT = 3000;

app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'sharpsheet-api' });
});

// Generate spritesheet endpoint
app.post('/generate', async (req, res) => {
  const {
    inputPath,
    outputPath,
    format = 'jpg',
    quality = 60,
    dimension = 2048,
    spriteSize = 128
  } = req.body;

  if (!inputPath || !outputPath) {
    return res.status(400).json({ 
      error: 'Missing required parameters: inputPath, outputPath' 
    });
  }

  console.log(`Generating spritesheet from ${inputPath} to ${outputPath}`);

  const input = `${inputPath}/*.jpg`;
  
  const options = {
    border: 1,
    sheetDimension: parseInt(dimension),
    sheetBackground: { r: 0, g: 0, b: 0, a: 0 },
    outputFormat: format,
    outputQuality: parseInt(quality),
    spriteSize: parseInt(spriteSize)
  };

  console.log('Input:', input);
  console.log('Output:', outputPath);
  console.log('Options:', options);

  try {
    const result = await sharpsheet(input, outputPath, options);
    
    console.log('Spritesheet generated successfully');
    res.json({
      success: true,
      message: 'Spritesheet generated successfully',
      outputPath,
      result
    });
  } catch (error) {
    console.error('Error generating spritesheet:', error);
    res.status(500).json({
      success: false,
      error: error.message,
      stack: error.stack
    });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Sharpsheet API server listening on port ${PORT}`);
});

