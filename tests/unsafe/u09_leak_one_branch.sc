// expect: leak
int main() {
    int n = 0;
    own int* p = alloc(4);
    *p = 1;
    if (n == 1) {
        free(p);
    }
    return 0;
}
