// Review example: the pointer may be freed on one path before the next use.
int main() {
    int should_release = 1;
    own int* buffer = alloc(4);
    if (should_release) {
        free(buffer);
    }
    *buffer = 42;
    free(buffer);
    return 0;
}
