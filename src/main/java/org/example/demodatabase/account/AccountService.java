package org.example.demodatabase.account;

import org.springframework.stereotype.Service;

@Service
public class AccountService {

    private final AccountRepository accountRepository;

    public AccountService(AccountRepository accountRepository) {
        this.accountRepository = accountRepository;
    }

    public Account get(Integer id) {
        return accountRepository.findById(id).orElseThrow();
    }

    public Account withdraw(Integer id, Integer amount) {
        Account account = accountRepository.findById(id).orElseThrow();
        Integer balance = account.getBalance();

        if (balance >= amount) {
            account.setBalance(balance - amount);
            return accountRepository.save(account);
        }

        throw new IllegalStateException("Insufficient funds: balance=" + balance + ", amount=" + amount);
    }
}
