// expect: safe
int main() {
    own int* a = alloc(4);
    own int* b = alloc(4);
    *a = 10;
    *b = *a + 5;
    print(*b);
    free(b);
    free(a);
    return 0;
}
