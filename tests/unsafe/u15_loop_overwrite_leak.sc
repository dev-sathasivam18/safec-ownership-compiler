// expect: leak
int main() {
    int i = 0;
    own int* p = alloc(4);
    while (i < 3) {
        p = alloc(4);
        i = i + 1;
    }
    free(p);
    return 0;
}
