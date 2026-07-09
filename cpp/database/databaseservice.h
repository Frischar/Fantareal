#pragma once

#include "database/databasemodels.h"
#include "database/databasepaths.h"

class DatabaseService final {
public:
    explicit DatabaseService(QString rootPath);

    DatabasePaths paths() const;
    DatabaseStatus ensureInitialized() const;
    DatabaseOverview overview() const;

private:
    DatabasePaths paths_;
};
