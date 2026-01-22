FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.11

# Install Node.js from Amazon Linux Extras
RUN yum install -y amazon-linux-extras && \
    amazon-linux-extras enable nodejs18 && \
    yum clean metadata && \
    yum install -y nodejs npm && \
    yum clean all

# Verify Node.js installation
RUN node --version && npm --version

# Install gltf-transform CLI globally
RUN npm install -g @gltf-transform/cli

# Verify gltf-transform installation
RUN which gltf-transform && gltf-transform --version

# Copy function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Install Python dependencies
RUN pip install boto3 --target "${LAMBDA_TASK_ROOT}"

# Set the CMD to your handler
CMD [ "lambda_function.lambda_handler" ]
