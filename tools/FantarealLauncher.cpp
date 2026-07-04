#include <windows.h>

#include <string>
#include <vector>

namespace {
std::wstring quoteArg(const std::wstring& value) {
    std::wstring out = L"\"";
    unsigned slashCount = 0;
    for (wchar_t ch : value) {
        if (ch == L'\\') {
            ++slashCount;
            out.push_back(ch);
        } else if (ch == L'"') {
            out.append(slashCount, L'\\');
            out.append(L"\\\"");
            slashCount = 0;
        } else {
            slashCount = 0;
            out.push_back(ch);
        }
    }
    out.append(slashCount, L'\\');
    out.push_back(L'"');
    return out;
}

std::wstring directoryOf(const std::wstring& path) {
    const size_t slash = path.find_last_of(L"\\/");
    return slash == std::wstring::npos ? L"." : path.substr(0, slash);
}

std::wstring buildChildCommandLine(const std::wstring& appPath, LPWSTR rawCommandLine) {
    std::wstring command = quoteArg(appPath);
    int argc = 0;
    LPWSTR* argv = CommandLineToArgvW(rawCommandLine, &argc);
    if (!argv) {
        return command;
    }
    for (int i = 1; i < argc; ++i) {
        command.push_back(L' ');
        command += quoteArg(argv[i]);
    }
    LocalFree(argv);
    return command;
}

void showError(const std::wstring& message) {
    MessageBoxW(nullptr, message.c_str(), L"Fantareal PC", MB_ICONERROR | MB_OK);
}
}

int WINAPI wWinMain(HINSTANCE, HINSTANCE, LPWSTR, int) {
    std::vector<wchar_t> exePath(MAX_PATH);
    DWORD copied = GetModuleFileNameW(nullptr, exePath.data(), static_cast<DWORD>(exePath.size()));
    while (copied == exePath.size()) {
        exePath.resize(exePath.size() * 2);
        copied = GetModuleFileNameW(nullptr, exePath.data(), static_cast<DWORD>(exePath.size()));
    }
    if (copied == 0) {
        showError(L"无法定位启动器路径。");
        return 1;
    }

    const std::wstring rootDir = directoryOf(std::wstring(exePath.data(), copied));
    const std::wstring appDir = rootDir + L"\\app";
    const std::wstring appPath = appDir + L"\\FantarealHuskarUI.exe";

    DWORD attr = GetFileAttributesW(appPath.c_str());
    if (attr == INVALID_FILE_ATTRIBUTES || (attr & FILE_ATTRIBUTE_DIRECTORY)) {
        showError(L"未找到 app\\FantarealHuskarUI.exe，请确认发布包完整解压。");
        return 2;
    }

    SetEnvironmentVariableW(L"FANTAREAL_ROOT", rootDir.c_str());
    const std::wstring qmlPath = appDir + L"\\HuskarUI\\qml;" + appDir + L"\\qml";
    SetEnvironmentVariableW(L"QML_IMPORT_PATH", qmlPath.c_str());

    std::wstring command = buildChildCommandLine(appPath, GetCommandLineW());
    std::vector<wchar_t> mutableCommand(command.begin(), command.end());
    mutableCommand.push_back(L'\0');

    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    PROCESS_INFORMATION process{};
    if (!CreateProcessW(appPath.c_str(),
                        mutableCommand.data(),
                        nullptr,
                        nullptr,
                        FALSE,
                        0,
                        nullptr,
                        rootDir.c_str(),
                        &startup,
                        &process)) {
        showError(L"启动 Fantareal PC 失败。");
        return 3;
    }

    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return 0;
}
