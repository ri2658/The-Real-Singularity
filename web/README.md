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

Do not deploy this with the PlantDex / DS3 profile (`AWS_PROFILE=plantdex`). That account is the paid plan. Ryo said this site stays on the AWS free plan, and nothing here has been deployed.

One-time, on a free-plan account only: install the AWS CLI, log in with that account, then from `infrastructure/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install -g aws-cdk
cdk bootstrap
cdk --app "python site_app.py" deploy BurgersSiteStack
```

The deploy prints `BucketName`, `DistributionId`, and `SiteUrl`. Then, from the repo root, with `boto3` installed:

```bash
python scripts/publish_site.py --bucket BUCKET --distribution DIST_ID
```

Wait until the CloudFront distribution is deployed (the first time can take several minutes), then open `SiteUrl` on a laptop and a phone. The sliders should redraw the curve.

`publish_site.py` sets the types the checkpoint calls for:

| File | Content type |
| --- | --- |
| `.wasm` | `application/wasm` |
| `.onnx` | `application/octet-stream` |
| `.html` | `text/html` |

Check the model response:

```bash
curl -sI https://YOUR_DOMAIN/pinn.onnx | grep -i content-type
```

It should say `application/octet-stream`.

To take the site down:

```bash
cd infrastructure
cdk --app "python site_app.py" destroy BurgersSiteStack
```
