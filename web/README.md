# Burgers PINN page

`index.html` loads `pinn.onnx` (the `p1000_8x20_s1` weights) and plots `u(x, t)`. The ONNX Runtime WebAssembly is loaded from jsDelivr, which already sends `application/wasm`. The model file is uploaded with `application/octet-stream`.

The PlantDex stack in `infrastructure/plantdex_stack.py` is a Lambda API. It cannot host this page. `infrastructure/burgers_site_stack.py` is a separate S3 bucket and CloudFront distribution.

## Try it on your machine

From the repo root:

```bash
python3 -m http.server 8765
```

Open http://127.0.0.1:8765/web/ . Open the same address on a phone only if the computer and the phone are on the same network and you use the computer's LAN address instead of `127.0.0.1`. A public phone test needs the CloudFront URL below.

## Deploy

The whole site (`site/`, this page included) lives on Charles's free-plan AWS account, as Ryo asked:
**https://d3hn8ndenpdwl3.cloudfront.net**. Do not use the PlantDex / DS3 profile (`AWS_PROFILE=plantdex`).

**Every update** (from the repo root):

```bash
python scripts/deploy.py             # build site/, sign in if needed, upload, refresh CloudFront
python scripts/deploy.py --dry-run   # build and list what would be uploaded
```

`deploy.py` rebuilds `site/` first, reuses your AWS sign-in (or opens `aws login` in the browser),
reads the bucket and distribution from the `BurgersSiteStack` outputs, then calls `publish_site.py`.
It needs the AWS CLI (`winget install -e --id Amazon.AWSCLI` on Windows) and a sign-in to the account
that holds the stack.

**One-time setup** (already done, Oct 30): from `infrastructure/`,

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install -g aws-cdk
cdk bootstrap
cdk --app "python site_app.py" deploy BurgersSiteStack
```

`publish_site.py` sets the types the checkpoint calls for:

| File | Content type |
| --- | --- |
| `.wasm` | `application/wasm` |
| `.onnx` | `application/octet-stream` |
| `.html` | `text/html` |

Check the model response:

```bash
curl -sI https://d3hn8ndenpdwl3.cloudfront.net/pinn/pinn.onnx | grep -i content-type
```

It should say `application/octet-stream`.

To take the site down:

```bash
cd infrastructure
cdk --app "python site_app.py" destroy BurgersSiteStack
```
