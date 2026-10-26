// expect: double-free
int main() {
    own int* a = alloc(4);
    free(a);
    free(a);
    return 0;
}
