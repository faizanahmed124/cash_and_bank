from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

from cash_and_bank import __version__ as version

setup(
	name="cash_and_bank",
	version=version,
	description="Cash & Bank -- Approval for Payment, Cheque wizard, plus curated Payments, Receipts, Masters, Reconciliation and Banking views on top of ERPNext",
	author="ATS Synthetic (Pvt) Ltd.",
	author_email="it@atssynthetic.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
)
