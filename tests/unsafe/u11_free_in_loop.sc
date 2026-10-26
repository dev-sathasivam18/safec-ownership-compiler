// expect: double-free
int main() {
    int i = 0;
    own int* p = alloc(4);
    while (i < 2) {
        free(p);
        i = i + 1;
    }
    return 0;
}
