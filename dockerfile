FROM public.ecr.aws/lambda/python:3.12

# Copy requirements.txt
COPY requirements.txt .

# Install the specified packages
RUN pip install -r requirements.txt

# Copy function code
COPY src/merge.py ${LAMBDA_TASK_ROOT}
COPY src/query.py ${LAMBDA_TASK_ROOT}
COPY src/prepare.py ${LAMBDA_TASK_ROOT}

# Install extensions
RUN python ${LAMBDA_TASK_ROOT}/prepare.py

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "query.handler" ]
