import oci
import os
import time
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# OCI AUTHENTICATION
# ============================================================

config = {
    "user": os.getenv("OCI_USER_ID"),
    "key_content": os.getenv("OCI_PRIVATE_KEY"),
    "fingerprint": os.getenv("OCI_FINGERPRINT"),
    "tenancy": os.getenv("OCI_TENANCY_ID"),
    "region": os.getenv("OCI_REGION")
}

try:
    compute_client = oci.core.ComputeClient(config)
    print("OCI Authentication Successful.")
    print(f"Region: {config['region']}")

except Exception as e:
    print(f"Authentication Failed: {e}")
    exit(1)


# ============================================================
# EXECUTION PARAMETERS
# ============================================================

compartment_id = os.getenv("OCI_TENANCY_ID")
subnet_id = os.getenv("OCI_SUBNET_ID")
image_id = os.getenv("OCI_IMAGE_ID")
public_ssh_key = os.getenv("OCI_PUBLIC_SSH_KEY")


# ============================================================
# SAFETY CHECKS
# ============================================================

if not compartment_id:
    print("CRITICAL ERROR: OCI_TENANCY_ID is empty or missing.")
    exit(1)

if not subnet_id:
    print("CRITICAL ERROR: OCI_SUBNET_ID is empty or missing.")
    exit(1)

if not image_id:
    print("CRITICAL ERROR: OCI_IMAGE_ID is empty or missing.")
    exit(1)

if not public_ssh_key or public_ssh_key.strip() == "":
    print("CRITICAL ERROR: OCI_PUBLIC_SSH_KEY is empty or missing.")
    exit(1)


# ============================================================
# INSTANCE CONFIGURATION
# ============================================================

display_name = "endure-vps"

# Your São Paulo Availability Domain
availability_domain = "YIaV:SA-SAOPAULO-1-AD-1"

# Always Free Ampere A1
shape = "VM.Standard.A1.Flex"

# Always Free maximum allocation
ocpus = 2
memory_in_gbs = 12

# Boot volume
boot_volume_size_in_gbs = 50


# ============================================================
# RETRY CONFIGURATION
# ============================================================

# Change this number to control how many attempts are made.
#
# 60 attempts = approximately 1 hour
# 120 attempts = approximately 2 hours
# 360 attempts = approximately 6 hours
#
total_attempts = 600

# One attempt every 60 seconds
retry_seconds = 60


# ============================================================
# DISPLAY CONFIGURATION
# ============================================================

print()
print("=" * 60)
print("ENDURE OCI A1 PROVISIONER")
print("=" * 60)
print(f"Region:              {config['region']}")
print(f"Availability Domain: {availability_domain}")
print(f"Shape:               {shape}")
print(f"OCPU:                {ocpus}")
print(f"Memory:              {memory_in_gbs} GB")
print(f"Boot volume:         {boot_volume_size_in_gbs} GB")
print(f"Total attempts:      {total_attempts}")
print(f"Retry interval:      {retry_seconds} seconds")
print("=" * 60)
print()


# ============================================================
# PROVISIONING LOOP
# ============================================================

for i in range(1, total_attempts + 1):

    print(
        f"[Attempt {i}/{total_attempts}] "
        f"Requesting instance '{display_name}'..."
    )

    try:

        request = oci.core.models.LaunchInstanceDetails(
            display_name=display_name,

            compartment_id=compartment_id,

            availability_domain=availability_domain,

            shape=shape,

            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=ocpus,
                memory_in_gbs=memory_in_gbs
            ),

            source_details=oci.core.models.InstanceSourceViaImageDetails(
                source_type="image",
                image_id=image_id,
                boot_volume_size_in_gbs=boot_volume_size_in_gbs
            ),

            create_vnic_details=oci.core.models.CreateVnicDetails(
                subnet_id=subnet_id,
                assign_public_ip=True,
                assign_private_dns_record=True
            ),

            metadata={
                "ssh_authorized_keys": public_ssh_key.strip()
            }
        )

        response = compute_client.launch_instance(request)

        # If launch_instance returns without an exception,
        # OCI accepted the creation request.
        print()
        print("=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print(f"Instance OCID: {response.data.id}")
        print("OCI accepted the instance creation request.")
        print("=" * 60)

        exit(0)


    except oci.exceptions.ServiceError as e:

        error_text = str(e)

        # ----------------------------------------------------
        # EXPECTED ERROR WHILE WAITING FOR A1 CAPACITY
        # ----------------------------------------------------

        if "Out of host capacity" in error_text:

            print(
                f"-> Out of host capacity. "
                f"Waiting {retry_seconds} seconds before retry..."
            )

        # ----------------------------------------------------
        # OTHER OCI ERRORS
        # ----------------------------------------------------

        else:

            print()
            print("=" * 60)
            print("OCI API ERROR")
            print("=" * 60)
            print(f"HTTP Status: {e.status}")
            print(f"Error Code:  {e.code}")
            print(f"Message:     {e.message}")
            print("=" * 60)

            # Do NOT keep retrying errors such as:
            # - invalid image
            # - invalid subnet
            # - authorization problems
            # - invalid parameters
            # - wrong region
            #
            # Those are configuration errors, not capacity errors.

            exit(1)


    except Exception as e:

        print()
        print("=" * 60)
        print("UNEXPECTED ERROR")
        print("=" * 60)
        print(str(e))
        print("=" * 60)

        exit(1)


    # ========================================================
    # WAIT BEFORE NEXT ATTEMPT
    # ========================================================

    if i < total_attempts:

        print(
            f"Waiting {retry_seconds} seconds "
            f"before attempt {i + 1}/{total_attempts}..."
        )

        time.sleep(retry_seconds)


# ============================================================
# ALL ATTEMPTS EXHAUSTED
# ============================================================

print()
print("=" * 60)
print("NO CAPACITY AVAILABLE")
print("=" * 60)
print(
    f"All {total_attempts} attempts were exhausted "
    f"without obtaining an A1 host."
)
print("=" * 60)

exit(1)
