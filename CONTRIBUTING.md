# Contributing Guidelines

Thank you for contributing to the Epson L3110 All-in-One Print & Scan Server project!

---

## 📜 Development Guidelines

1. **Language Policy**:
   - Python 3.10+ for hardware drivers, WIA COM bindings, and IPP.
   - Node.js for Web UI, gateway routing, and frontend static asset delivery.
   - **Zero C# or .NET**: Pull requests introducing .NET assemblies, C# projects, or CLR-dependent scripts will not be merged.
2. **Windows Compatibility**:
   - Code must execute reliably on standard Windows 11 (and Windows 10) systems.
   - Any COM interaction with WIA or Shell must correctly manage `CoInitialize` / `CoUninitialize` scopes.
3. **Submitting Changes**:
   - Fork the repository.
   - Create a feature branch (`git checkout -b feature/awesome-feature`).
   - Commit your changes with descriptive commit messages.
   - Push to the branch and open a Pull Request.
