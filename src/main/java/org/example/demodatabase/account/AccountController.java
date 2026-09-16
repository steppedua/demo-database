package org.example.demodatabase.account;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/accounts")
public class AccountController {

    private final AccountService accountService;

    public AccountController(AccountService accountService) {
        this.accountService = accountService;
    }

    @GetMapping("/{id}")
    public Account get(@PathVariable Integer id) {
        return accountService.get(id);
    }

    @PostMapping("/{id}/withdraw")
    public Account withdraw(@PathVariable Integer id, @RequestParam Integer amount) {
        return accountService.withdraw(id, amount);
    }
}
