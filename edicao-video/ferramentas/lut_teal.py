"""Build a 33^3 .cube LUT reproducing the reference grade: crushed blacks, highlight roll-off (never clipping),
neutrals and cool tones pushed to teal/cyan (R ~ 0.83 x G on neutral objects), skin protected and kept warm.
usage: lut_teal.py out.cube [strength=1.0] [black=0.07] [white=0.90] [skin_warm=1.0] [contrast=1.0]
Also: lut_teal.py --preview frame.png out.png ... applies the LUT to a still for checking."""
import sys, numpy as np

def grade(rgb, strength=1.0, black=0.07, white=0.90, skin_warm=1.0, contrast=1.0, skin_sat=1.0):
    """rgb float (...,3) 0..1 -> graded"""
    x = np.clip(rgb, 0, 1)
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    mx = x.max(-1); mn = x.min(-1); c = mx - mn
    # hue in degrees
    h = np.zeros_like(mx)
    m = c > 1e-6
    rr = np.where(m & (mx == r), ((g - b) / np.where(m, c, 1)) % 6, 0)
    gg = np.where(m & (mx == g), (b - r) / np.where(m, c, 1) + 2, 0)
    bb = np.where(m & (mx == b), (r - g) / np.where(m, c, 1) + 4, 0)
    h = np.where(mx == r, rr, np.where(mx == g, gg, bb)) * 60
    sat = np.where(mx > 1e-6, c / np.maximum(mx, 1e-6), 0)
    # skin weight: warm hues 5-45 deg, some saturation, not too dark
    dh = np.minimum(np.abs(h - 22), 360 - np.abs(h - 22))
    w_skin = np.exp(-(dh / 16) ** 2) * np.clip((sat - 0.12) / 0.15, 0, 1) * np.clip((mx - 0.18) / 0.15, 0, 1)
    # --- tone + colour. Teal version: per-channel curves (neutrals and highlights go cyan, R ~ 0.84 x G up top).
    #     Warm version (skin): one luminance curve for all channels plus a little warmth.
    k = strength
    def curve(v, xs, ys):
        return np.interp(v, xs, ys)
    xs_r = [0, black, .137, .216, .50, .745, .90, 1]; ys_r = [0, 0, .031, .050, .47 - .03 * (k - 1), .68, .78, .84]
    xs_g = [0, black, .176, .55, .75, 1];              ys_g = [0, .015, .150, .58, .78, .93]
    xs_b = [0, black, .196, .45, .75, 1];              ys_b = [0, .027, .180, .48, .78, .95]
    teal = np.stack([curve(r, xs_r, ys_r), curve(g, xs_g, ys_g), curve(b, xs_b, ys_b)], -1)
    teal = x * (1 - k) + teal * k if k < 1 else teal
    lum_x = [0, black, .176, .55, .80, 1]; lum_y = [0, .01, .14, .58, .82, white]
    s_ = np.stack([curve(r, lum_x, lum_y), curve(g, lum_x, lum_y), curve(b, lum_x, lum_y)], -1)
    warm = s_ * np.array([1 + 0.03 * skin_warm, 1.0, 1 - 0.05 * skin_warm])
    out = teal * (1 - w_skin[..., None]) + warm * w_skin[..., None]
    # saturation: +10 %
    l = out.mean(-1, keepdims=True)
    # warm hues (skin, blond hair) get skin_sat instead of the +10 %
    dhw = np.minimum(np.abs(h - 30), 360 - np.abs(h - 30))
    w_warm = np.exp(-(dhw / 20) ** 2) * np.clip((sat - 0.10) / 0.15, 0, 1)
    out = l + (out - l) * (1.10 * (1 - w_warm[..., None]) + skin_sat * w_warm[..., None])
    return np.clip(out, 0, 1)

def write_cube(path, n=33, **kw):
    grid = np.linspace(0, 1, n)
    b, g, r = np.meshgrid(grid, grid, grid, indexing='ij')   # r fastest in .cube
    rgb = np.stack([r, g, b], -1).reshape(-1, 3)
    out = grade(rgb, **kw)
    with open(path, 'w') as f:
        f.write(f'TITLE "teal-orange reference"\nLUT_3D_SIZE {n}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        for v in out:
            f.write(f'{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n')

if __name__ == '__main__':
    if sys.argv[1] == '--preview':
        from PIL import Image
        im = np.asarray(Image.open(sys.argv[2]).convert('RGB'), np.float32) / 255
        kw = dict(zip(['strength', 'black', 'white', 'skin_warm', 'contrast', 'skin_sat'], map(float, sys.argv[4:])))
        Image.fromarray((grade(im, **kw) * 255 + .5).astype(np.uint8)).save(sys.argv[3])
    else:
        kw = dict(zip(['strength', 'black', 'white', 'skin_warm', 'contrast', 'skin_sat'], map(float, sys.argv[2:])))
        write_cube(sys.argv[1], **kw)
        print('wrote', sys.argv[1], kw)
