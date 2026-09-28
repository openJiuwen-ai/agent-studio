#!/usr/bin/env python3
import ipaddress
import os
import shutil
import subprocess


IPV4_INTERNAL_CIDRS = (
    '0.0.0.0/8',
    '10.0.0.0/8',
    '127.0.0.0/8',
    '169.254.0.0/16',
    '172.16.0.0/12',
    '192.168.0.0/16',
)

IPV6_INTERNAL_CIDRS = (
    '::1/128',
    '::/128',
    'fc00::/7',
    'fe80::/10',
)

CHAIN_V4 = 'OJ_SANDBOX_BLOCK_INT'
CHAIN_V6 = 'OJ_SANDBOX_BLOCK_INT6'


def apply_internal_network_guard(run_user='app'):
    """Block private/internal destinations for processes owned by run_user."""
    if os.name != 'posix':
        return

    uid = _resolve_uid(run_user)
    dns_servers = _read_dns_servers()

    _configure_family(
        binary='iptables',
        chain=CHAIN_V4,
        uid=uid,
        internal_cidrs=IPV4_INTERNAL_CIDRS,
        dns_servers=[ip for ip in dns_servers if ip.version == 4],
    )
    _configure_family(
        binary='ip6tables',
        chain=CHAIN_V6,
        uid=uid,
        internal_cidrs=IPV6_INTERNAL_CIDRS,
        dns_servers=[ip for ip in dns_servers if ip.version == 6],
    )


def _resolve_uid(run_user):
    if str(run_user).isdigit():
        return str(run_user)
    import pwd

    try:
        return str(pwd.getpwnam(run_user).pw_uid)
    except KeyError as e:
        raise RuntimeError(f'Cannot find sandbox run user: {run_user}') from e


def _read_dns_servers():
    servers = []
    try:
        with open('/etc/resolv.conf', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[0] == 'nameserver':
                    try:
                        servers.append(ipaddress.ip_address(parts[1]))
                    except ValueError:
                        continue
    except OSError:
        pass
    return servers


def _configure_family(binary, chain, uid, internal_cidrs, dns_servers):
    if not shutil.which(binary):
        raise RuntimeError(f'{binary} is required to enforce sandbox network guard rules.')

    if _run([binary, '-w', '-L', chain, '-n'], check=False).returncode != 0:
        _run([binary, '-w', '-N', chain])
    else:
        _run([binary, '-w', '-F', chain])

    for dns_server in dns_servers:
        dst = f'{dns_server}/32' if dns_server.version == 4 else f'{dns_server}/128'
        if dns_server.is_loopback:
            # Docker's 127.0.0.11 DNS can be DNATed to a loopback high port.
            _run([binary, '-w', '-A', chain, '-d', dst, '-j', 'RETURN'])
        else:
            _run([binary, '-w', '-A', chain, '-d', dst, '-p', 'udp', '--dport', '53', '-j', 'RETURN'])
            _run([binary, '-w', '-A', chain, '-d', dst, '-p', 'tcp', '--dport', '53', '-j', 'RETURN'])

    for cidr in internal_cidrs:
        _run([binary, '-w', '-A', chain, '-d', cidr, '-j', 'REJECT'])

    jump_rule = [binary, '-w', '-C', 'OUTPUT', '-m', 'owner', '--uid-owner', uid, '-j', chain]
    if _run(jump_rule, check=False).returncode != 0:
        _run([binary, '-w', '-I', 'OUTPUT', '1', '-m', 'owner', '--uid-owner', uid, '-j', chain])


def _run(cmd, check=True):
    env = os.environ.copy()
    env.setdefault('XTABLES_LOCKFILE', '/tmp/openjiuwen_sandbox_xtables.lock')
    try:
        result = subprocess.run(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f'Command timed out after 30s: {" ".join(cmd)}') from exc
    if check and result.returncode != 0:
        raise RuntimeError(f'Command failed: {" ".join(cmd)}\n{result.stderr.strip()}')
    return result
