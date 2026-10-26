// expect: safe
void countdown(own int* box) {
    if (*box == 0) {
        free(box);
        return;
    }
    print(*box);
    *box = *box - 1;
    countdown(box);
}
int main() {
    own int* b = alloc(4);
    *b = 3;
    countdown(b);
    return 0;
}
