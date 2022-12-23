import os
from urllib.parse import urlsplit
from g import templates_dir, config_dir, data_dir, DEFAULT_UID, DEFAULT_GID

from .jinja import render_jinja
from .misc import prepare_dir

chart_museum_temp_dir = os.path.join(templates_dir, "chartserver")
chart_museum_env_temp = os.path.join(chart_museum_temp_dir, "env.jinja")

chart_museum_config_dir = os.path.join(config_dir, "chartserver")
chart_museum_env = os.path.join(config_dir, "chartserver", "env")

chart_museum_data_dir = os.path.join(data_dir, 'chart_storage')


def parse_redis(redis_url_chart):
    u = urlsplit(redis_url_chart)
    if not u.scheme or u.scheme == 'redis':
        return {
            'cache_store': 'redis',
            'cache_redis_addr': u.netloc.split('@')[-1],
            'cache_redis_password': u.password or '',
            'cache_redis_db_index': u.path and int(u.path[1:]) or 0,
        }
    elif u.scheme == 'redis+sentinel':
        return {
            'cache_store': 'redis_sentinel',
            'cache_redis_mastername': u.path.split('/')[1],
            'cache_redis_addr': u.netloc.split('@')[-1],
            'cache_redis_password': u.password or '',
            'cache_redis_db_index': len(u.path.split('/')) == 3 and int(u.path.split('/')[2]) or 0,
        }
    else:
        raise Exception(f'bad redis url for chart:{redis_url_chart}')


def prepare_chartmuseum(config_dict):
    storage_provider_name = config_dict['storage_provider_name']
    storage_provider_config_map = config_dict['storage_provider_config']

    prepare_dir(chart_museum_data_dir, uid=DEFAULT_UID, gid=DEFAULT_GID)
    prepare_dir(chart_museum_config_dir)

    # process redis info
    cache_redis_ops = parse_redis(config_dict['redis_url_chart'])


    # process storage info
    #default using local file system
    storage_driver = "local"
    # storage provider configurations
    # please be aware that, we do not check the validations of the values for the specified keys
    # convert the configs to config map
    storage_provider_config_options = []
    if storage_provider_name == 'azure':
        # azure storage
        storage_driver = "microsoft"
        storage_provider_config_options.extend(
            (
                f"""STORAGE_MICROSOFT_CONTAINER={storage_provider_config_map.get("container") or ''}""",
                f"""AZURE_STORAGE_ACCOUNT={storage_provider_config_map.get("accountname") or ''}""",
                f"""AZURE_STORAGE_ACCESS_KEY={storage_provider_config_map.get("accountkey") or ''}""",
                "STORAGE_MICROSOFT_PREFIX=/azure/harbor/charts",
            )
        )
    elif storage_provider_name == 'gcs':
        # google cloud storage
        storage_driver = "google"
        storage_provider_config_options.extend(
            (
                f"""STORAGE_GOOGLE_BUCKET={storage_provider_config_map.get("bucket") or ''}""",
                f"""STORAGE_GOOGLE_PREFIX={storage_provider_config_map.get("rootdirectory") or ''}""",
            )
        )
        if storage_provider_config_map.get("keyfile"):
            storage_provider_config_options.append(
                f"GOOGLE_APPLICATION_CREDENTIALS={'/etc/chartserver/gcs.key'}"
            )
    elif storage_provider_name == 'oss':
        # aliyun OSS
        storage_driver = "alibaba"
        bucket = storage_provider_config_map.get("bucket") or ''
        endpoint = storage_provider_config_map.get("endpoint") or ''
        if endpoint.startswith(f"{bucket}."):
            endpoint = endpoint.replace(f"{bucket}.", "")
        storage_provider_config_options.extend(
            (
                f"STORAGE_ALIBABA_BUCKET={bucket}",
                f"STORAGE_ALIBABA_ENDPOINT={endpoint}",
                f"""STORAGE_ALIBABA_PREFIX={storage_provider_config_map.get("rootdirectory") or ''}""",
                f"""ALIBABA_CLOUD_ACCESS_KEY_ID={storage_provider_config_map.get("accesskeyid") or ''}""",
                f"""ALIBABA_CLOUD_ACCESS_KEY_SECRET={storage_provider_config_map.get("accesskeysecret") or ''}""",
            )
        )
    elif storage_provider_name == 's3':
        # aws s3 storage
        storage_driver = "amazon"
        storage_provider_config_options.extend(
            (
                f"""STORAGE_AMAZON_BUCKET={storage_provider_config_map.get("bucket") or ''}""",
                f"""STORAGE_AMAZON_PREFIX={storage_provider_config_map.get("rootdirectory") or ''}""",
                f"""STORAGE_AMAZON_REGION={storage_provider_config_map.get("region") or ''}""",
                f"""STORAGE_AMAZON_ENDPOINT={storage_provider_config_map.get("regionendpoint") or ''}""",
                f"""AWS_ACCESS_KEY_ID={storage_provider_config_map.get("accesskey") or ''}""",
                f"""AWS_SECRET_ACCESS_KEY={storage_provider_config_map.get("secretkey") or ''}""",
            )
        )
    elif storage_provider_name == 'swift':
        # open stack swift
        storage_driver = "openstack"
        storage_provider_config_options.extend(
            (
                f"""STORAGE_OPENSTACK_CONTAINER={storage_provider_config_map.get("container") or ''}""",
                f"""STORAGE_OPENSTACK_PREFIX={storage_provider_config_map.get("rootdirectory") or ''}""",
                f"""STORAGE_OPENSTACK_REGION={storage_provider_config_map.get("region") or ''}""",
                f"""OS_AUTH_URL={storage_provider_config_map.get("authurl") or ''}""",
                f"""OS_USERNAME={storage_provider_config_map.get("username") or ''}""",
                f"""OS_PASSWORD={storage_provider_config_map.get("password") or ''}""",
                f"""OS_PROJECT_ID={storage_provider_config_map.get("tenantid") or ''}""",
                f"""OS_PROJECT_NAME={storage_provider_config_map.get("tenant") or ''}""",
                "OS_DOMAIN_ID=%s"
                % (storage_provider_config_map.get("domainid") or ''),
                "OS_DOMAIN_NAME=%s"
                % (storage_provider_config_map.get("domain") or ''),
            )
        )
    else:
        # use local file system
        storage_provider_config_options.append("STORAGE_LOCAL_ROOTDIR=/chart_storage")

    # generate storage provider configuration
    all_storage_provider_configs = ('\n').join(storage_provider_config_options)

    render_jinja(
        chart_museum_env_temp,
        chart_museum_env,
        storage_driver=storage_driver,
        all_storage_driver_configs=all_storage_provider_configs,
        public_url=config_dict['public_url'],
        chart_absolute_url=config_dict['chart_absolute_url'],
        internal_tls=config_dict['internal_tls'],
        **cache_redis_ops)
