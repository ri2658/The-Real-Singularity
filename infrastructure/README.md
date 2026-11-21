# Infrastructure

AWS CDK app for the website: one stack, `BurgersSiteStack`, defined in `burgers_site_stack.py` and created by
`site_app.py`. It is a private S3 bucket behind a CloudFront distribution, in Charles's free-plan AWS account
(us-east-2). The live site is **https://d3hn8ndenpdwl3.cloudfront.net**.

You only need this folder to create or delete the stack. Day-to-day updates go through `scripts/deploy.py`
(see the main README).

```bash
cd infrastructure
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
npm install -g aws-cdk
cdk bootstrap                      # once per account and region
cdk deploy                         # creates BurgersSiteStack
cdk destroy                        # takes the site down
```
