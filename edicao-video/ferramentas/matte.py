"""Person alpha matte with RobustVideoMatting (ONNX). Writes lossless gray FFV1 alpha video.
usage: matte.py in.mp4 out_alpha.mkv W H [model] [downsample] [max_seconds]"""
import os as _os
EDV = _os.environ.get('EDV_HOME', _os.path.expanduser('~/edicao-video-dados'))
import sys, subprocess, numpy as np, onnxruntime as ort, time
src, out, W, H = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
model = sys.argv[5] if len(sys.argv)>5 else 'mobilenetv3'
ds = float(sys.argv[6]) if len(sys.argv)>6 else 0.25
maxs = sys.argv[7] if len(sys.argv)>7 else None
M=f'{EDV}/models/rvm/rvm_{model}_fp32.onnx'
so=ort.SessionOptions(); so.intra_op_num_threads=4
sess=ort.InferenceSession(M, so, providers=['CPUExecutionProvider'])
cmd=['ffmpeg','-v','error','-i',src]+(['-t',maxs] if maxs else [])+['-vf',f'scale={W}:{H}','-f','rawvideo','-pix_fmt','rgb24','-']
dec=subprocess.Popen(cmd,stdout=subprocess.PIPE)
enc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','gray','-s',f'{W}x{H}','-r','30','-i','-','-c:v','ffv1','-pix_fmt','gray',out],stdin=subprocess.PIPE)
rec=[np.zeros([1,1,1,1],np.float32)]*4; dr=np.array([ds],np.float32)
n=0; t0=time.time(); fs=W*H*3
while True:
    buf=dec.stdout.read(fs)
    if len(buf)<fs: break
    img=np.frombuffer(buf,np.uint8).reshape(H,W,3).astype(np.float32).transpose(2,0,1)[None]/255.
    fgr,pha,*rec=sess.run(None,{'src':img,'r1i':rec[0],'r2i':rec[1],'r3i':rec[2],'r4i':rec[3],'downsample_ratio':dr})
    enc.stdin.write((np.clip(pha[0,0],0,1)*255+0.5).astype(np.uint8).tobytes()); n+=1
enc.stdin.close(); enc.wait()
print(f'{n} frames in {time.time()-t0:.1f}s ({n/(time.time()-t0):.1f} fps)')
