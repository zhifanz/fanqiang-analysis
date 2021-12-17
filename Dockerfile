FROM public.ecr.aws/lambda/python:3.8 as base

COPY . ${LAMBDA_TASK_ROOT}/

FROM base as fanqiang-extract-domain
CMD [ "process_aws_cloudwatch_shadowsocks_logs.handler" ]

FROM base as fanqiang-update-rules
CMD ["calculate_routing_rules.handler"]

FROM base as fanqiang-update-ping
ENTRYPOINT ["python3", "ping_statistics.py"]
CMD ["--days", "30", "--pingcount", "10", "domains", "cn"]
