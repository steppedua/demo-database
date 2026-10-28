package org.example.demodatabase.account;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class AccountService {

    private final AccountRepository accountRepository;

    public Account get(Integer id) {
        return accountRepository.findById(id).orElseThrow();
    }
}
