import io
import os
import pathlib

import jc
import paramiko
import pulumi
import pulumi_aws
import pulumi_alicloud
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from minerule.shellagent import RemoteCommandError, ShellAgent


def test_ed25519():
    key_pair = Ed25519()
    assert key_pair.public_key.decode("ascii")
    assert key_pair.private_key.decode("ascii")


def test_pkey():
    with open("/Users/zhifan/.ssh/id_ed25519", mode="rb") as f:
        assert paramiko.Ed25519Key.from_private_key(f)


class TestShellAgent:
    def test_ssh_auth_central(self, central_shell: ShellAgent):
        result = central_shell.connection.run("echo -n hello", hide=True)
        assert result.stdout == "hello"

    def test_ssh_auth_domestic(self, domestic_shell: ShellAgent):
        result = domestic_shell.connection.run("echo -n hello", hide=True)
        assert result.stdout == "hello"

    def test_ping_central(self, central_shell: ShellAgent):
        result = central_shell.ping("baidu.com", 10)
        assert result.packets_transmitted == 10
        assert result.packets_received > 0
        assert result.destination_ip
        assert result.round_trip_ms_avg
        assert result.round_trip_ms_min
        assert result.round_trip_ms_max
        assert result.round_trip_ms_stddev

    def test_ping_domestic(self, domestic_shell: ShellAgent):
        result = domestic_shell.ping("baidu.com", 10)
        assert result.packets_transmitted == 10
        assert result.packets_received > 0
        assert result.destination_ip
        assert result.round_trip_ms_avg
        assert result.round_trip_ms_min
        assert result.round_trip_ms_max
        assert result.round_trip_ms_stddev

    def test_ping_failed(self, domestic_shell: ShellAgent):
        with pytest.raises(RemoteCommandError):
            domestic_shell.ping("google.com", 10)

    def test_dig_central(self, central_shell: ShellAgent):
        result = central_shell.dig("baidu.com")
        assert len(result.a) > 0

    def test_dig_domestic(self, domestic_shell: ShellAgent):
        result = domestic_shell.dig("baidu.com")
        assert len(result.a) > 0

    def test_jc_ping(self):
        content = (pathlib.Path(__file__).parent / "ping_stdout").read_text()
        result = jc.parse("ping", content)
        assert result["destination_ip"] == "14.215.177.38"
        assert result["packets_transmitted"] == 3
        assert result["packets_received"] == 3
        assert result["round_trip_ms_min"] == 0.113
        assert result["round_trip_ms_avg"] == 0.223
        assert result["round_trip_ms_max"] == 0.292
        assert result["round_trip_ms_stddev"] == 0.078

    def test_jc_dig(self):
        content = (pathlib.Path(__file__).parent / "dig_stdout").read_text()
        result = jc.parse("dig", content)
        assert result[0]["answer_num"] == 2


class Ed25519:
    def __init__(self) -> None:
        key = ed25519.Ed25519PrivateKey.generate()
        self.public_key = (
            key.public_key()
            .public_bytes(
                serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
            )
            .decode("ascii")
        )

        self.private_key = paramiko.Ed25519Key.from_private_key(
            io.StringIO(
                key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.OpenSSH,
                    serialization.NoEncryption(),
                ).decode("ascii")
            )
        )


def pulumi_lightsail(public_key: str):
    r = pulumi_aws.lightsail.Instance(
        "default",
        availability_zone="us-east-1b",
        blueprint_id="amazon_linux_2",
        bundle_id="nano_2_0",
        key_pair_name=pulumi_aws.lightsail.KeyPair(
            "default", public_key=public_key
        ).name,
    )
    pulumi.export("public_ip", r.public_ip_address)


def pulumi_aliyun(public_key: str):
    alicloud_vpc = pulumi_alicloud.vpc.Network("default", cidr_block="192.168.0.0/16")
    alicloud_security_group = pulumi_alicloud.ecs.SecurityGroup(
        "default", inner_access_policy="Accept", vpc_id=alicloud_vpc.id
    )
    pulumi_alicloud.ecs.SecurityGroupRule(
        "default",
        ip_protocol="tcp",
        security_group_id=alicloud_security_group.id,
        type="ingress",
        port_range="22/22",
        cidr_ip="0.0.0.0/0",
    )
    ecs_type = pulumi_alicloud.ecs.get_instance_types(
        cpu_core_count=1,
        memory_size=0.5,
        network_type="Vpc",
        system_disk_category="cloud_efficiency",
    ).instance_types[0]
    domestic_instance = pulumi_alicloud.ecs.Instance(
        "default",
        image_id="aliyun_2_1903_x64_20G_alibase_20210726.vhd",
        instance_type=ecs_type.id,
        security_groups=[alicloud_security_group.id],
        internet_max_bandwidth_out=100,
        force_delete=True,
        key_name=pulumi_alicloud.ecs.KeyPair("default", public_key=public_key).key_name,
        vswitch_id=pulumi_alicloud.vpc.Switch(
            "default",
            cidr_block="192.168.0.0/24",
            vpc_id=alicloud_vpc.id,
            zone_id=ecs_type.availability_zones[0],
        ).id,
    )
    pulumi.export("public_ip", domestic_instance.public_ip)


def infra(program, name, key_pair) -> pulumi.automation.Stack:
    stack = pulumi.automation.create_or_select_stack(
        name,
        os.path.basename(os.getcwd()),
        lambda: program(key_pair.public_key),
    )
    stack.workspace.install_plugin("aws", "v5.1.0")
    stack.workspace.install_plugin("alicloud", "v3.19.0")
    stack.set_config("alicloud:profile", pulumi.automation.ConfigValue("default"))
    stack.up(on_output=print)
    return stack


@pytest.fixture(scope="class")
def central_shell() -> ShellAgent:
    key_pair = Ed25519()
    stack = infra(pulumi_lightsail, "test_shellagent_lightsail", key_pair)
    yield ShellAgent(
        stack.outputs()["public_ip"].value,
        "ec2-user",
        key_pair.private_key,
    )
    stack.destroy()
    stack.workspace.remove_stack(stack.name)


@pytest.fixture(scope="class")
def domestic_shell() -> ShellAgent:
    key_pair = Ed25519()
    stack = infra(pulumi_aliyun, "test_shellagent_aliyun", key_pair)
    yield ShellAgent(
        stack.outputs()["public_ip"].value,
        "root",
        key_pair.private_key,
    )
    stack.destroy()
    stack.workspace.remove_stack(stack.name)
