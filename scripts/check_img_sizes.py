import os
from PIL import Image

fig_dir = r"C:\Users\GOPAL\OneDrive\Desktop\AURA-IEEE-Paper\figures"
for f in sorted(os.listdir(fig_dir)):
    if f.endswith(('.png', '.jpg', '.jpeg')):
        p = os.path.join(fig_dir, f)
        im = Image.open(p)
        w, h = im.size
        aspect = h / w
        h_pt_at_30 = (3.0 * aspect) * 72
        h_pt_at_32 = (3.2 * aspect) * 72
        print(f"{f:25s}: {w}x{h} (aspect={aspect:.3f}) -> at 3.0 in: {h_pt_at_30:.1f} pt, at 3.2 in: {h_pt_at_32:.1f} pt")
