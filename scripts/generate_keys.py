#!/usr/bin/env python3
"""PULSAR SENTINEL - Key Generation Script.

Generates ML-KEM or AES keys for testing and development.

Usage:
    python generate_keys.py --algorithm hybrid --output keys/
    python generate_keys.py --algorithm aes --output keys/
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))


def generate_hybrid_keys(security_level: int = 768) -> dict:
    """Generate ML-KEM hybrid encryption keys.

    Args:
        security_level: ML-KEM security level (768 or 1024)

    Returns:
        Dictionary with key information
    """
    try:
        from core.pqc import HybridEncryptor
        encryptor = HybridEncryptor(security_level=security_level)
        keypair = encryptor.generate_keypair()

        return {
            "algorithm": keypair.algorithm,
            "security_level": security_level,
            "key_id": keypair.key_id,
            "public_key": base64.b64encode(keypair.public_key).decode(),
            "secret_key": base64.b64encode(keypair.secret_key).decode(),
            "created_at": keypair.created_at.isoformat(),
            "public_key_hash": keypair.public_key_hash,
        }
    except ImportError:
        print("Warning: liboqs not available, using simulated keys")
        from core.pqc import PQCEngineSimulated
        engine = PQCEngineSimulated(security_level=security_level)
        keypair = engine.generate_keypair()

        return {
            "algorithm": f"SIMULATED-ML-KEM-{security_level}",
            "security_level": security_level,
            "key_id": keypair.key_id,
            "public_key": base64.b64encode(keypair.public_key).decode(),
            "secret_key": base64.b64encode(keypair.secret_key).decode(),
            "created_at": keypair.created_at.isoformat(),
            "public_key_hash": keypair.public_key_hash,
            "warning": "SIMULATED - NOT QUANTUM RESISTANT",
        }


def generate_aes_keys() -> dict:
    """Generate AES-256 encryption keys.

    Returns:
        Dictionary with key information
    """
    from core.legacy import LegacyCrypto

    crypto = LegacyCrypto()
    password = os.urandom(32)
    key, salt = crypto.derive_key(password)

    key_id = base64.b64encode(os.urandom(8)).decode()

    return {
        "algorithm": "AES-256-CBC-HMAC-SHA256",
        "key_id": key_id,
        "key": base64.b64encode(key).decode(),
        "salt": base64.b64encode(salt).decode(),
        "password": base64.b64encode(password).decode(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_ecdsa_keys() -> dict:
    """Generate ECDSA secp256k1 keys for Polygon.

    Returns:
        Dictionary with key information
    """
    from core.legacy import ECDSASigner

    signer = ECDSASigner.generate()
    keypair = signer.get_keypair()

    return {
        "algorithm": "ECDSA-secp256k1",
        "address": keypair.address,
        "private_key": base64.b64encode(keypair.private_key).decode(),
        "public_key": base64.b64encode(keypair.public_key).decode(),
        "created_at": keypair.created_at.isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(
        description="PULSAR SENTINEL Key Generation"
    )
    parser.add_argument(
        "--algorithm",
        choices=["hybrid", "aes", "ecdsa", "all"],
        default="hybrid",
        help="Key algorithm to generate",
    )
    parser.add_argument(
        "--security-level",
        type=int,
        choices=[768, 1024],
        default=768,
        help="ML-KEM security level",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=".",
        help="Output directory",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON to stdout",
    )

    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    if args.algorithm in ("hybrid", "all"):
        print(f"Generating ML-KEM-{args.security_level} keys...")
        results["hybrid"] = generate_hybrid_keys(args.security_level)

    if args.algorithm in ("aes", "all"):
        print("Generating AES-256 keys...")
        results["aes"] = generate_aes_keys()

    if args.algorithm in ("ecdsa", "all"):
        print("Generating ECDSA secp256k1 keys...")
        results["ecdsa"] = generate_ecdsa_keys()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Save to files
        for key_type, key_data in results.items():
            filename = output_dir / f"{key_type}_keys.json"
            with open(filename, "w") as f:
                json.dump(key_data, f, indent=2)
            print(f"Saved: {filename}")

            # Print summary
            print(f"\n{key_type.upper()} Key Summary:")
            print(f"  Algorithm: {key_data['algorithm']}")
            if "key_id" in key_data:
                print(f"  Key ID: {key_data['key_id']}")
            if "address" in key_data:
                print(f"  Address: {key_data['address']}")
            if "warning" in key_data:
                print(f"  WARNING: {key_data['warning']}")

    print("\nKey generation complete!")


if __name__ == "__main__":
    main()
