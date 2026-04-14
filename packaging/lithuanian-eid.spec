%global python3_pkgversion 3

Name:           lithuanian-eid
Version:        0.1.0
Release:        1%{?dist}
Summary:        Lithuanian electronic ID tools

License:        GPL-3.0-only
URL:            https://github.com/tadas-s/lithuanian-eid
Source:         %{url}/archive/v%{version}/lithuanian_eid-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python%{python3_pkgversion}-devel
Requires:       opensc >= 0.27, pinentry

%generate_buildrequires
%pyproject_buildrequires


%description
Software suite to use Lithuanian electronic ID via OpenSC for
authentication and electronic signatures.


%prep
%autosetup -p1 -n lithuanian_eid-%{version}


%build
%pyproject_wheel


%install
%pyproject_install

%check
%pytest


%files
%doc README.md
%license LICENSE
%{python3_sitelib}/lithuanian_eid/
%{python3_sitelib}/lithuanian_eid-*.dist-info/
%{_bindir}/lteid_server
%{_bindir}/lteid_toolbox

%changelog
* Sat Mar 01 2025 Tadas Sasnauskas <tadas@yoyo.lt> - 0.1.0
- First release
