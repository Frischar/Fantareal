#pragma once

#include "database/databasemodels.h"
#include "database/databasepaths.h"

class DatabaseRepository final {
public:
    explicit DatabaseRepository(DatabasePaths paths);

    DatabaseStatus initializeSchema() const;
    DatabaseOverview describe() const;

private:
    DatabasePaths paths_;
};
