// expect: safe
int main() {
    int i = 0;
    while (i < 3) {
        own int* t = alloc(4);
        *t = i * 10;
        print(*t);
        free(t);
        i = i + 1;
    }
    return 0;
}
