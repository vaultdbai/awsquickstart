FROM public.ecr.aws/lambda/python:3.12

# Copy requirements.txt
COPY requirements.txt .

# Install the specified packages
RUN pip install -r requirements.txt

# Install vaultdb
RUN dnf install -y tar gzip
COPY resources/vaultdb_python312.tar.gz /tmp/
RUN tar -xf /tmp/vaultdb_python312.tar.gz -C /var/lang/lib/python3.12/site-packages/
RUN rm -rf /tmp/vaultdb_python312.tar.gz
RUN dnf remove -y tar gzip

# Copy function code
COPY src/merge.py ${LAMBDA_TASK_ROOT}
COPY src/query.py ${LAMBDA_TASK_ROOT}
COPY src/prepare.py ${LAMBDA_TASK_ROOT}

# Install extensions
RUN python ${LAMBDA_TASK_ROOT}/prepare.py

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "query.handler" ]
