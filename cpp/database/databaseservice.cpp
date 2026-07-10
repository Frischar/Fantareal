#include "database/databaseservice.h"

#include "database/databaserepository.h"

#include <utility>

DatabaseService::DatabaseService(QString rootPath)
    : paths_(std::move(rootPath)) {
}

DatabasePaths DatabaseService::paths() const {
    return paths_;
}

DatabaseStatus DatabaseService::ensureInitialized() const {
    DatabaseRepository repository(paths_);
    return repository.initializeSchema();
}

DatabaseOverview DatabaseService::overview() const {
    DatabaseRepository repository(paths_);
    return repository.describe();
}
