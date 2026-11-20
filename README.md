# Music Painter

**A desktop app that turns a WAV file or live audio into one 2-D geometric image.**

[Download for Windows, macOS or Linux at musicpainter.org](https://musicpainter.org) · [Website source](https://github.com/ktranfaglia1/MusicPainterWebsite)

<p align="center"><img src="icons/Logo.png" alt="Music Painter logo" width="160"></p>

Music Painter treats music as visual art. It reads audio from a WAV file or a microphone stream and splits it into chunks. It runs a Fast Fourier Transform on each chunk to find the dominant frequency and the spectral data, then paints that data onto a canvas as points, lines, circles, rectangles and triangles. The result is a single image of the whole clip.

It began as an undergraduate research project at Salisbury University, built with a mathematics student under a faculty mentor, and was accepted at five conferences.

## Features

- **Two audio sources:** load one WAV file or a whole folder of them, or capture live audio from any input device.
- **13 visualization algorithms**, each mapping frequency and spectral data to shape, color and position in its own way:

  | | | | |
  |---|---|---|---|
  | Frequency Dots | Dynamite | Ball of Yarn | 3-D Symmetry |
  | Spirograph | Colorful Void | Vortex | Illuminate Snake |
  | Triangle Stacker | Spiraling Circles | Circulating Squares | Sporadic Squares |
  | Emotional Progression *(beta)* | | | |

  Emotional Progression picks color schemes meant to reflect the emotion of the audio.
- **Render modes:** render instantly, or render and play so the image builds while the audio plays.
- **Adjustable FFT window:** chunk sizes from 1,024 to 131,072 samples, which trade time resolution for frequency resolution.
- **Recording:** record a live stream and save it as a WAV file.
- **Canvas:** zoom with the scroll wheel, drag to pan, reset the view, and change the background color.
- **Output:** save the image, copy it to the clipboard, or print it with a print preview.
- **Settings:** choose input and output devices, set output volume, view file information, and pick a Qt theme.

## How it works

1. The WAV data, or the incoming stream, is split into fixed-size chunks.
2. For each chunk, `numpy.fft.rfft` and `rfftfreq` produce the magnitude spectrum and the dominant frequency.
3. `PaintBrush.py` passes that data to the selected algorithm, which emits geometric primitives (points, lines, circles, rectangles, triangles) into a render list.
4. The canvas widget in `MusicPainter.py` draws the render list with `QPainter`, either all at once or in step with playback.

## Tech stack

- **Python 3.9**
- **PySide2** (Qt for Python) for the GUI, rendering and printing
- **NumPy** for the FFT and spectral analysis; **SciPy** for reading WAV files
- **PyAudio** for live input, playback and audio-device selection
- Distributed as standalone executables for Windows, macOS and Linux (the code supports PyInstaller-style bundling through `resource_path`)

## Running from source

```bash
pip install PySide2 numpy scipy pyaudio
python MusicPainter.py
```

- PySide2 supports Python up to 3.10, so use Python 3.9 or 3.10.
- PyAudio needs the PortAudio library:
  - Linux: `sudo apt install portaudio19-dev`
  - macOS: `brew install portaudio`

## Repository structure

```
├── MusicPainter.py   # Main window, audio input/output, FFT, canvas and rendering
├── PaintBrush.py     # The 13 visualization algorithms and drawing primitives
└── icons/            # App logo and toolbar icons
```

## Recognition

- National Conference on Undergraduate Research (NCUR), April 2024
- Northeast Regional Honors Council Conference (NRHC), April 2024
- Posters on the Bay, February 2024
- Middle States Commission on Higher Education annual conference (MSCHE), November 2023
- Salisbury University Student Research Conference (SUSRC), April 2023

## Authors

- **[Kyle Tranfaglia](https://github.com/ktranfaglia1)**: developer and researcher
- **Luke Zolenski**: co-developer (mathematics)
- **Dr. Don Spickler**: faculty mentor and co-author

Salisbury University.
