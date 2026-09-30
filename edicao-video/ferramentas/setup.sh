#!/bin/bash
# Instala dependências e baixa modelos e fontes para a pasta de dados (EDV_HOME, padrão ~/edicao-video-dados).
set -e
S=${EDV_HOME:-$HOME/edicao-video-dados}; mkdir -p $S/models/rvm $S/fonts $S/pylibs $S/work
pip install -q imageio-ffmpeg sherpa-onnx onnxruntime numpy scipy pillow soundfile opencv-python-headless
pip install -q --target $S/pylibs "opencv-python-headless<5" "numpy<2.3"
FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"); ln -sf "$FF" /usr/local/bin/ffmpeg 2>/dev/null || true
B=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models
cd $S/models
[ -f silero_vad.onnx ] || curl -sS -L -O $B/silero_vad.onnx
[ -d sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8 ] || curl -sS -L $B/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8.tar.bz2 | tar xj
[ -d sherpa-onnx-whisper-turbo ] || curl -sS -L $B/sherpa-onnx-whisper-turbo.tar.bz2 | tar xj
cd rvm; [ -f rvm_mobilenetv3_fp32.onnx ] || curl -sS -L -O https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx
cd $S/fonts
get() { u=$(curl -sS "https://fonts.googleapis.com/css2?family=$1" | grep -oE "url\([^)]+\)" | head -1 | sed 's/url(//;s/)//'); curl -sS -o "$2" "$u"; }
[ -f BebasNeue-Regular.ttf ] || get "Bebas+Neue" BebasNeue-Regular.ttf
[ -f InstrumentSans-Bold.ttf ] || get "Instrument+Sans:wght@700" InstrumentSans-Bold.ttf
[ -f Inter-Bold.ttf ] || get "Inter:wght@700" Inter-Bold.ttf
[ -f Inter-Medium.ttf ] || get "Inter:wght@500" Inter-Medium.ttf
[ -f Inter-Regular.ttf ] || get "Inter:wght@400" Inter-Regular.ttf
echo "pronto: $S"
